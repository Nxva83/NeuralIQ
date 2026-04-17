"""
RiftIQ — Module Coach IA (LLM)
================================
Utilise Ollama (Mistral 7B) en local pour générer des conseils
personnalisés basés sur les stats + données des heatmaps K-Means.

Usage standalone :
    python coach.py --name "TonPseudo" --tag "EUW"

Ou via l'API FastAPI :
    GET /api/coach/{name}/{tag}
    POST /api/coach/chat  (chat interactif)
"""

import json, os, requests, argparse
from collections import defaultdict

OLLAMA_URL  = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
DATA_DIR    = "data"
OUTPUT_DIR  = "output"

# ─── Chargement des données ────────────────────────────────────────────────────

def load_player_data(name: str, tag: str) -> dict:
    """Charge et structure toutes les données disponibles pour le joueur."""

    # Matchs
    match_path = f"{DATA_DIR}/matches_{name}_{tag}.json"
    matches = json.load(open(match_path)) if os.path.exists(match_path) else []

    # Rapport heatmap
    report_path = f"{OUTPUT_DIR}/rapport_{name}_{tag}.txt"
    heatmap_report = open(report_path).read() if os.path.exists(report_path) else ""

    if not matches:
        raise FileNotFoundError(f"Aucune donnée pour {name}#{tag}. Lance riot_pipeline.py d'abord.")

    # ── Calcul des stats globales ──
    total  = len(matches)
    wins   = sum(1 for m in matches if m["won"])
    winrate = round(wins / total * 100)
    avg_kda = round(sum(m["kda"] for m in matches) / total, 2)
    avg_hs  = round(sum(m["headshot_pct"] for m in matches) / total, 1)
    avg_acs = round(sum(m["acs"] for m in matches) / total)
    avg_dmg = round(sum(m["damage_made"] for m in matches) / total)

    # ── Stats par agent ──
    agent_stats = defaultdict(lambda: {"wins": 0, "total": 0, "kda_sum": 0})
    for m in matches:
        a = m["agent"]
        agent_stats[a]["total"] += 1
        agent_stats[a]["kda_sum"] += m["kda"]
        if m["won"]: agent_stats[a]["wins"] += 1

    agents = sorted([
        {
            "name": a,
            "games": s["total"],
            "winrate": round(s["wins"] / s["total"] * 100),
            "avg_kda": round(s["kda_sum"] / s["total"], 2)
        }
        for a, s in agent_stats.items()
    ], key=lambda x: x["games"], reverse=True)

    # ── Stats par map ──
    map_stats = defaultdict(lambda: {"wins": 0, "total": 0})
    for m in matches:
        mp = m.get("map_name", "Unknown")
        map_stats[mp]["total"] += 1
        if m["won"]: map_stats[mp]["wins"] += 1

    maps = sorted([
        {
            "name": mp,
            "games": s["total"],
            "winrate": round(s["wins"] / s["total"] * 100)
        }
        for mp, s in map_stats.items()
    ], key=lambda x: x["games"], reverse=True)

    # ── Tendance récente (5 derniers matchs) ──
    recent = matches[:5]
    recent_wins   = sum(1 for m in recent if m["won"])
    recent_wr     = round(recent_wins / len(recent) * 100) if recent else 0
    recent_kda    = round(sum(m["kda"] for m in recent) / len(recent), 2) if recent else 0
    recent_agents = [m["agent"] for m in recent]

    # ── Map la plus faible et la plus forte ──
    maps_with_enough = [m for m in maps if m["games"] >= 2]
    worst_map = min(maps_with_enough, key=lambda x: x["winrate"])["name"] if maps_with_enough else "inconnue"
    best_map  = max(maps_with_enough, key=lambda x: x["winrate"])["name"] if maps_with_enough else "inconnue"

    return {
        "player":        f"{name}#{tag}",
        "total_matches": total,
        "winrate":       winrate,
        "avg_kda":       avg_kda,
        "avg_hs":        avg_hs,
        "avg_acs":       avg_acs,
        "avg_dmg":       avg_dmg,
        "agents":        agents[:5],
        "maps":          maps,
        "worst_map":     worst_map,
        "best_map":      best_map,
        "recent_wr":     recent_wr,
        "recent_kda":    recent_kda,
        "recent_agents": recent_agents,
        "heatmap_report": heatmap_report,
        "raw_matches":   matches,
    }


# ─── Construction du prompt ────────────────────────────────────────────────────

def build_prompt(data: dict, question: str = None) -> str:
    """
    Construit un prompt structuré et riche pour Mistral.
    Combine stats + données des heatmaps K-Means pour un coaching précis.
    """

    agents_str = "\n".join([
        f"  - {a['name']}: {a['games']} parties, {a['winrate']}% WR, KDA {a['avg_kda']}"
        for a in data["agents"]
    ])

    maps_str = "\n".join([
        f"  - {m['name']}: {m['games']} parties, {m['winrate']}% WR"
        for m in data["maps"]
    ])

    heatmap_section = ""
    if data["heatmap_report"]:
        heatmap_section = f"""
=== ANALYSE DES ZONES DE JEU (K-Means Clustering) ===
{data["heatmap_report"]}
"""

    prompt = f"""Tu es RiftIQ, un coach IA expert en Valorant compétitif.
Tu analyses les données de parties d'un joueur et tu donnes des conseils précis, actionnables et bienveillants.
Tu parles en français, avec un ton coach professionnel mais accessible.
Tu connais parfaitement le méta Valorant, les callouts des maps, les rôles des agents.

=== PROFIL DU JOUEUR ===
Joueur    : {data["player"]}
Matchs analysés : {data["total_matches"]}
Winrate   : {data["winrate"]}%
KDA moyen : {data["avg_kda"]}
HS% moyen : {data["avg_hs"]}%
ACS moyen : {data["avg_acs"]}
Dégâts/match : {data["avg_dmg"]}

=== AGENTS JOUÉS ===
{agents_str}

=== PERFORMANCES PAR MAP ===
{maps_str}

Meilleure map : {data["best_map"]}
Map la plus faible : {data["worst_map"]}

=== TENDANCE RÉCENTE (5 derniers matchs) ===
Winrate récent : {data["recent_wr"]}%
KDA récent     : {data["recent_kda"]}
Agents récents : {", ".join(data["recent_agents"])}
{heatmap_section}
=== CONSIGNES DE COACHING ===
- Analyse les données ci-dessus avec l'œil d'un coach professionnel
- Identifie les 3 axes d'amélioration PRIORITAIRES et CONCRETS
- Pour chaque axe, donne un conseil spécifique et actionnable
- Mentionne les patterns des heatmaps si disponibles (zones dangereuses, mauvais positionnements)
- Termine par un encouragement motivant adapté au niveau du joueur
- Sois précis : cite les maps, les agents, les chiffres du profil
- Format : structuré avec des sections claires
"""

    if question:
        prompt += f"\n=== QUESTION DU JOUEUR ===\n{question}\n\nRéponds précisément à cette question en t'appuyant sur les données ci-dessus."
    else:
        prompt += "\n=== GÉNÈRE LE RAPPORT DE COACHING ==="

    return prompt


# ─── Appel Ollama ──────────────────────────────────────────────────────────────

def ask_ollama(prompt: str, stream: bool = False) -> str:
    """Envoie le prompt à Ollama et retourne la réponse complète."""
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 1024,
        }
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    if not resp.ok:
        raise RuntimeError(f"Ollama erreur {resp.status_code}: {resp.text[:200]}")

    if stream:
        return resp  # retourne l'objet response pour streaming
    else:
        return resp.json().get("response", "")


def ask_ollama_stream(prompt: str):
    """Generator qui stream la réponse token par token."""
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.7, "top_p": 0.9, "num_predict": 1024}
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


# ─── Fonctions publiques ───────────────────────────────────────────────────────

def generate_coaching_report(name: str, tag: str) -> str:
    """Génère un rapport de coaching complet pour un joueur."""
    print(f"🧠 Chargement des données pour {name}#{tag}...")
    data   = load_player_data(name, tag)
    prompt = build_prompt(data)

    print(f"🤖 Mistral analyse {data['total_matches']} matchs + heatmaps...")
    print("─" * 50)

    response = ""
    for token in ask_ollama_stream(prompt):
        print(token, end="", flush=True)
        response += token

    print("\n" + "─" * 50)

    # Sauvegarde
    out_path = f"{OUTPUT_DIR}/coaching_{name}_{tag}.txt"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"=== Rapport de coaching RiftIQ — {name}#{tag} ===\n\n")
        f.write(response)
    print(f"\n💾 Rapport sauvegardé : {out_path}")

    return response


def ask_coach(name: str, tag: str, question: str) -> str:
    """Répond à une question spécifique du joueur."""
    data   = load_player_data(name, tag)
    prompt = build_prompt(data, question=question)

    response = ""
    for token in ask_ollama_stream(prompt):
        response += token
    return response


# ─── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RiftIQ — Coach IA Mistral")
    parser.add_argument("--name",     required=True)
    parser.add_argument("--tag",      required=True)
    parser.add_argument("--question", default=None,
                        help="Pose une question spécifique au coach")
    args = parser.parse_args()

    if args.question:
        print(f"\n🎮 Question : {args.question}\n")
        data   = load_player_data(args.name, args.tag)
        prompt = build_prompt(data, question=args.question)
        print("─" * 50)
        for token in ask_ollama_stream(prompt):
            print(token, end="", flush=True)
        print("\n")
    else:
        generate_coaching_report(args.name, args.tag)
