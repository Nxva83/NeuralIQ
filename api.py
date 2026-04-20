"""
RiftIQ — API FastAPI complète
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import json, os, glob, tempfile, asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/heatmaps", StaticFiles(directory="output"), name="heatmaps")

DATA_DIR = "data"

# ─── Données joueur ───────────────────────────────────────────────────────────

@app.get("/api/player/{name}/{tag}")
def get_player(name: str, tag: str):
    path = f"{DATA_DIR}/player_{name}_{tag}.json"
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, 404)
    return json.load(open(path))

@app.get("/api/matches/{name}/{tag}")
def get_matches(name: str, tag: str):
    path = f"{DATA_DIR}/matches_{name}_{tag}.json"
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, 404)
    return json.load(open(path))

@app.get("/api/heatmaps/{name}/{tag}")
def get_heatmaps(name: str, tag: str):
    files = glob.glob("output/heatmap_*.png")
    maps  = {}
    for f in sorted(files):
        base  = os.path.basename(f).replace("heatmap_", "").replace(".png", "")
        parts = base.rsplit("_", 1)
        if len(parts) == 2:
            map_name, event_type = parts
            if map_name not in maps:
                maps[map_name] = {}
            maps[map_name][event_type] = f"/heatmaps/{os.path.basename(f)}"
    return maps

@app.get("/api/report/{name}/{tag}")
def get_report(name: str, tag: str):
    path = f"output/rapport_{name}_{tag}.txt"
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, 404)
    return {"text": open(path).read()}

# ─── Coach IA global ──────────────────────────────────────────────────────────

from coach import load_player_data, build_prompt, ask_ollama_stream as coach_stream

class ChatRequest(BaseModel):
    question: str

@app.get("/api/coach/{name}/{tag}")
async def get_coaching(name: str, tag: str):
    try:
        data   = load_player_data(name, tag)
        prompt = build_prompt(data)
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, 404)

    async def stream():
        for token in coach_stream(prompt):
            yield token.encode("utf-8")

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")

@app.post("/api/coach/{name}/{tag}/chat")
async def chat_coach(name: str, tag: str, body: ChatRequest):
    try:
        data   = load_player_data(name, tag)
        prompt = build_prompt(data, question=body.question)
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, 404)

    async def stream():
        for token in coach_stream(prompt):
            yield token.encode("utf-8")

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")

# ─── Coach IA par match ───────────────────────────────────────────────────────

from match_coach import (
    fetch_match_detail, parse_match_detail,
    build_match_prompt, ask_ollama_stream as match_stream
)

@app.get("/api/match-coach/{name}/{tag}/{match_id}")
async def analyze_match(name: str, tag: str, match_id: str):
    try:
        raw    = fetch_match_detail(match_id)
        detail = parse_match_detail(raw, name, tag)
        prompt = build_match_prompt(detail, f"{name}#{tag}")
    except Exception as e:
        print(f"ERREUR MATCH COACH: {e}")
        import traceback; traceback.print_exc()
        return JSONResponse({"error": str(e)}, 400)

    async def stream():
        for token in match_stream(prompt):
            yield token.encode("utf-8")

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")

@app.post("/api/match-coach/{name}/{tag}/{match_id}/chat")
async def chat_match(name: str, tag: str, match_id: str, body: ChatRequest):
    try:
        raw    = fetch_match_detail(match_id)
        detail = parse_match_detail(raw, name, tag)
        prompt = (
            build_match_prompt(detail, f"{name}#{tag}") +
            f"\n\n=== QUESTION DE SUIVI ===\n{body.question}\n\n"
            "Réponds précisément en te basant sur les données du match ci-dessus."
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, 400)

    async def stream():
        for token in match_stream(prompt):
            yield token.encode("utf-8")

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")

# ─── Coach Vidéo ──────────────────────────────────────────────────────────────

from video_coach import (
    extract_key_frames, analyze_positioning,
    extract_minimap, analyze_minimap_frame, synthesize_analysis
)

@app.post("/api/video-coach")
async def video_coach(video: UploadFile = File(...), n_frames: int = 8):
    async def process():
        suffix = Path(video.filename).suffix if video.filename else ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await video.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            yield (json.dumps({"progress": "📸 Extraction des frames clés..."}) + "\n").encode()

            loop   = asyncio.get_event_loop()
            frames = await loop.run_in_executor(
                None, extract_key_frames, tmp_path, min(n_frames, 12)
            )

            analyses = []
            for i, frame in enumerate(frames, 1):
                yield (json.dumps({
                    "progress": f"🎯 Analyse frame {i}/{len(frames)} ({frame['timestamp']}s)..."
                }) + "\n").encode()

                positioning = await loop.run_in_executor(
                    None, analyze_positioning, frame["b64"], frame["timestamp"]
                )
                minimap_b64 = extract_minimap(frame["b64"])
                minimap_analysis = await loop.run_in_executor(
                    None, analyze_minimap_frame, minimap_b64, frame["timestamp"]
                )

                analyses.append({
                    "timestamp":   frame["timestamp"],
                    "positioning": positioning,
                    "minimap":     minimap_analysis,
                })

            yield (json.dumps({"progress": "🧠 Synthèse finale par Mistral..."}) + "\n").encode()

            synthesis = await loop.run_in_executor(None, synthesize_analysis, analyses)

            result = {
                "video":    video.filename,
                "n_frames": len(frames),
                "analyses": analyses,
                "synthesis": synthesis,
            }
            yield (json.dumps({"result": result}) + "\n").encode()

        finally:
            os.unlink(tmp_path)

    return StreamingResponse(process(), media_type="application/x-ndjson")