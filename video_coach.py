"""
RiftIQ — Analyse vidéo via LLaVA (Computer Vision)
====================================================
Extrait des frames clés d'un MP4 Valorant et utilise LLaVA
pour analyser le positionnement sur site et la minimap.

Usage:
    python video_coach.py --video ma_partie.mp4
    python video_coach.py --video ma_partie.mp4 --frames 10
"""

import os, json, base64, argparse, requests
import cv2
import numpy as np
from pathlib import Path

OLLAMA_URL   = "http://localhost:11434/api/generate"
LLAVA_MODEL  = "llava"
MISTRAL_MODEL = "mistral"

# ─── Extraction de frames ──────────────────────────────────────────────────────

def extract_key_frames(video_path: str, n_frames: int = 8) -> list[dict]:
    """
    Extrait N frames clés réparties uniformément dans la vidéo.
    Retourne une liste de dicts avec timestamp et image encodée en base64.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo : {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    duration     = total_frames / fps if fps > 0 else 0

    print(f"  📹 Vidéo : {total_frames} frames, {fps:.1f} FPS, {duration:.1f}s")

    # Sélectionne les indices de frames à extraire
    # On évite les 5 premières et dernières secondes (chargement/score)
    start_frame = int(fps * 5)
    end_frame   = max(total_frames - int(fps * 5), start_frame + 1)
    indices     = np.linspace(start_frame, end_frame, n_frames, dtype=int)

    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret:
            continue

        timestamp = idx / fps if fps > 0 else 0

        # Redimensionne pour réduire la taille (LLaVA accepte jusqu'à 1024px)
        h, w = frame.shape[:2]
        if w > 1024:
            scale = 1024 / w
            frame = cv2.resize(frame, (1024, int(h * scale)))

        # Encode en JPEG base64
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64    = base64.b64encode(buf).decode("utf-8")

        frames.append({
            "index":     int(idx),
            "timestamp": round(timestamp, 1),
            "b64":       b64,
            "shape":     frame.shape,
        })

    cap.release()
    print(f"  ✅ {len(frames)} frames extraites")
    return frames


def extract_minimap(frame_b64: str) -> str:
    """
    Extrait la zone minimap d'une frame Valorant.
    La minimap est typiquement dans le coin bas-gauche (~15% de la largeur).
    Retourne la minimap encodée en base64.
    """
    # Décode l'image
    img_bytes = base64.b64decode(frame_b64)
    img_arr   = np.frombuffer(img_bytes, dtype=np.uint8)
    img       = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

    h, w = img.shape[:2]

    # Zone minimap Valorant : coin bas-gauche, ~18% de la largeur, ~22% de la hauteur
    minimap_w = int(w * 0.18)
    minimap_h = int(h * 0.22)
    minimap   = img[h - minimap_h:h, 0:minimap_w]

    if minimap.size == 0:
        return frame_b64  # fallback sur la frame complète

    _, buf = cv2.imencode(".jpg", minimap, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buf).decode("utf-8")


# ─── Analyse LLaVA ────────────────────────────────────────────────────────────

def analyze_frame_llava(frame_b64: str, prompt: str) -> str:
    """Envoie une frame à LLaVA pour analyse."""
    payload = {
        "model":  LLAVA_MODEL,
        "prompt": prompt,
        "images": [frame_b64],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 300}
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    if not resp.ok:
        raise RuntimeError(f"LLaVA erreur {resp.status_code}")
    return resp.json().get("response", "")


def analyze_positioning(frame_b64: str, timestamp: float) -> str:
    """Analyse le positionnement sur site à partir d'une frame."""
    prompt = f"""This is a screenshot from a Valorant competitive match at {timestamp:.1f}s.
Analyze the player's positioning and provide feedback in French.

Focus on:
1. POSITIONNEMENT : Le joueur est-il en position agressive ou défensive ? Est-il exposé ou couvert ?
2. ANGLES : Quels angles sont contrôlés ? Y a-t-il des angles dangereux non couverts ?
3. COUVERTURE : Le joueur utilise-t-il bien les couverts disponibles ?
4. VISIBILITÉ : Le joueur peut-il être facilement spotté par des ennemis ?

Réponds en français, de manière concise (3-4 phrases max).
Si l'image n'est pas assez claire, dis-le simplement."""

    return analyze_frame_llava(frame_b64, prompt)


def analyze_minimap_frame(minimap_b64: str, timestamp: float) -> str:
    """Analyse la minimap pour les rotations et le spacing."""
    prompt = f"""This is the minimap from a Valorant match at {timestamp:.1f}s.
Analyze the team positioning shown on the minimap and provide feedback in French.

Focus on:
1. ROTATIONS : Les joueurs sont-ils bien positionnés pour des rotations rapides ?
2. SPACING : L'équipe est-elle trop groupée ou bien espacée ?
3. CONTRÔLE DE MAP : Quelles zones sont contrôlées/abandonnées ?
4. DANGER : Y a-t-il des positions isolées ou vulnérables visibles ?

Réponds en français, de manière concise (3-4 phrases max).
Si la minimap n'est pas visible, dis-le simplement."""

    return analyze_frame_llava(minimap_b64, prompt)


# ─── Synthèse Mistral ─────────────────────────────────────────────────────────

def synthesize_analysis(analyses: list[dict]) -> str:
    """
    Utilise Mistral pour synthétiser toutes les analyses de frames
    en un rapport de coaching cohérent.
    """
    analyses_text = ""
    for i, a in enumerate(analyses, 1):
        analyses_text += f"\n--- Frame {i} ({a['timestamp']}s) ---\n"
        if a.get("positioning"):
            analyses_text += f"Positionnement : {a['positioning']}\n"
        if a.get("minimap"):
            analyses_text += f"Minimap : {a['minimap']}\n"

    prompt = f"""Tu es RiftIQ, un coach IA expert Valorant.
Tu as analysé {len(analyses)} moments clés d'une partie via Computer Vision.
Voici les observations frame par frame :

{analyses_text}

En te basant sur ces observations :
1. Identifie les PATTERNS récurrents de mauvais positionnement
2. Identifie les PATTERNS récurrents de mauvaise lecture de minimap
3. Donne 3 conseils CONCRETS et ACTIONNABLES
4. Propose un exercice spécifique pour corriger le problème principal

Réponds en français, de manière structurée et encourageante.
Sois précis : cite les timestamps des moments clés."""

    payload = {
        "model":   MISTRAL_MODEL,
        "prompt":  prompt,
        "stream":  False,
        "options": {"temperature": 0.6, "num_predict": 800}
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    if not resp.ok:
        return "Erreur lors de la synthèse"
    return resp.json().get("response", "")


def ask_llava_stream(prompt: str, image_b64: str):
    """Stream LLaVA pour l'API FastAPI."""
    payload = {
        "model":   LLAVA_MODEL,
        "prompt":  prompt,
        "images":  [image_b64],
        "stream":  True,
        "options": {"temperature": 0.3, "num_predict": 400}
    }
    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120) as resp:
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break


# ─── Pipeline principal ────────────────────────────────────────────────────────

def analyze_video(video_path: str, n_frames: int = 8) -> dict:
    """
    Pipeline complet :
    1. Extraction des frames clés
    2. Analyse du positionnement par LLaVA
    3. Analyse de la minimap par LLaVA
    4. Synthèse par Mistral
    """
    print(f"\n{'═'*50}")
    print(f"  🎬 RiftIQ — Analyse vidéo")
    print(f"{'═'*50}\n")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Vidéo introuvable : {video_path}")

    # 1. Extraction des frames
    print("📸 Extraction des frames clés...")
    frames = extract_key_frames(video_path, n_frames)

    analyses = []
    for i, frame in enumerate(frames, 1):
        print(f"\n  [{i}/{len(frames)}] Analyse à {frame['timestamp']}s...")

        # 2. Analyse du positionnement
        print(f"    🎯 Positionnement...")
        positioning = analyze_positioning(frame["b64"], frame["timestamp"])
        print(f"    → {positioning[:80]}...")

        # 3. Extraction et analyse de la minimap
        print(f"    🗺️  Minimap...")
        minimap_b64 = extract_minimap(frame["b64"])
        minimap_analysis = analyze_minimap_frame(minimap_b64, frame["timestamp"])
        print(f"    → {minimap_analysis[:80]}...")

        analyses.append({
            "timestamp":   frame["timestamp"],
            "positioning": positioning,
            "minimap":     minimap_analysis,
        })

    # 4. Synthèse
    print(f"\n🧠 Synthèse par Mistral...")
    synthesis = synthesize_analysis(analyses)

    result = {
        "video":     os.path.basename(video_path),
        "n_frames":  len(frames),
        "analyses":  analyses,
        "synthesis": synthesis,
    }

    # Sauvegarde
    out_path = f"output/video_analysis_{Path(video_path).stem}.json"
    os.makedirs("output", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*50}")
    print("📊 SYNTHÈSE FINALE")
    print('─'*50)
    print(synthesis)
    print(f"\n💾 Résultats sauvegardés : {out_path}\n")

    return result


# ─── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RiftIQ — Analyse vidéo LLaVA")
    parser.add_argument("--video",  required=True, help="Chemin vers le fichier MP4")
    parser.add_argument("--frames", default=8, type=int,
                        help="Nombre de frames à analyser (défaut: 8)")
    args = parser.parse_args()
    analyze_video(args.video, args.frames)
