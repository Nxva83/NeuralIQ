"""
RiftIQ — Analyse détaillée d'un match spécifique
"""

import os, json, requests, time
from collections import defaultdict

def get_henrik_headers():
    key = os.getenv("HENRIK_API_KEY", "")
    return {"Authorization": key, "User-Agent": "RiftIQ-EIP/1.0"}

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"

def fetch_match_detail(match_id: str) -> dict:
    url  = f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}"
    resp = requests.get(url, headers=get_henrik_headers(), timeout=20)
    if resp.status_code == 429:
        time.sleep(12)
        return fetch_match_detail(match_id)
    if not resp.ok:
        raise RuntimeError(f"Henrik {resp.status_code}: {resp.text[:150]}")
    return resp.json().get("data", {})

def parse_match_detail(raw: dict, game_name: str, tag_line: str) -> dict:
    metadata    = raw.get("metadata", {})
    all_players = raw.get("players", {}).get("all_players", [])
    rounds      = raw.get("rounds", [])
    teams       = raw.get("teams", {})
    kills_raw   = raw.get("kills", [])

    my_id = f"{game_name}#{tag_line}".lower()

    me = next((p for p in all_players
               if f"{p.get('name')}#{p.get('tag')}".lower() == my_id), None)
    if not me:
        raise ValueError(f"Joueur {my_id} introuvable dans le match")

    team_id       = me.get("team", "").lower()
    my_team       = teams.get(team_id, {})
    won           = my_team.get("has_won", False)
    stats         = me.get("stats", {})
    economy       = me.get("economy", {})
    map_name      = metadata.get("map", "")
    rounds_played = metadata.get("rounds_played", 0)
    agent         = me.get("character", "")

    kills_count   = stats.get("kills",   0)
    deaths_count  = stats.get("deaths",  0)
    assists_count = stats.get("assists", 0)
    hs   = stats.get("headshots", 0)
    bs   = stats.get("bodyshots", 0)
    ls   = stats.get("legshots",  0)
    total_shots = hs + bs + ls
    hs_pct = round(hs / total_shots * 100, 1) if total_shots > 0 else 0

    spent_overall = economy.get("spent", {}).get("overall", 0)
    spent_avg     = economy.get("spent", {}).get("average", 0)
    loadout_avg   = economy.get("loadout_value", {}).get("average", 0)

    # ── Round par round ──
    round_details = []
    for rnd in rounds:
        rnd_num     = rnd.get("round_num", 0)
        win_team    = rnd.get("winning_team", "").lower()
        my_team_won = win_team == team_id

        my_pstat = next((p for p in rnd.get("player_stats", [])
                         if p.get("player_display_name", "").lower() == my_id), {})

        round_kills = len(my_pstat.get("kill_events", []))
        round_score = my_pstat.get("score", 0)

        early_kills = [ev for ev in my_pstat.get("kill_events", [])
                       if ev.get("kill_time_in_round", 99999) < 15000]

        round_details.append({
            "round":       rnd_num + 1,
            "won":         my_team_won,
            "kills":       round_kills,
            "early_kills": len(early_kills),
            "score":       round_score,
            "had_plant":   bool(rnd.get("plant_events")),
            "had_defuse":  bool(rnd.get("defuse_events")),
        })

    # ── Moments clés ──
    my_kills  = [ev for ev in kills_raw
                 if (ev.get("killer_display_name") or "").lower() == my_id]
    my_deaths = [ev for ev in kills_raw
                 if (ev.get("victim_display_name") or "").lower() == my_id]

    # First bloods
    first_bloods = 0
    for rnd in rounds:
        rnd_num = rnd.get("round_num", 0)
        rnd_kills_sorted = sorted(
            [ev for ev in kills_raw if ev.get("round") == rnd_num],
            key=lambda x: x.get("kill_time_in_round", 99999)
        )
        if rnd_kills_sorted:
            first_ev = rnd_kills_sorted[0]
            if (first_ev.get("killer_display_name") or "").lower() == my_id:
                first_bloods += 1

    early_deaths = sum(1 for ev in my_deaths if ev.get("kill_time_in_round", 99999) < 15000)
    late_deaths  = sum(1 for ev in my_deaths if ev.get("kill_time_in_round", 0)   > 60000)

    weapons = defaultdict(int)
    for ev in my_kills:
        w = ev.get("damage_weapon_name", "Unknown")
        weapons[w] += 1
    top_weapons = sorted(weapons.items(), key=lambda x: x[1], reverse=True)[:3]

    round_kill_counts = defaultdict(int)
    for ev in my_kills:
        round_kill_counts[ev.get("round", 0)] += 1
    multi_kills = {2: 0, 3: 0, 4: 0, 5: 0}
    for count in round_kill_counts.values():
        if count >= 2:
            key = min(count, 5)
            multi_kills[key] = multi_kills.get(key, 0) + 1

    team_players = [p for p in all_players if p.get("team", "").lower() == team_id]
    team_kills   = [p.get("stats", {}).get("kills", 0) for p in team_players]
    try:
        my_rank = sorted(team_kills, reverse=True).index(kills_count) + 1
    except ValueError:
        my_rank = "?"

    best_round = max(round_details, key=lambda r: r["score"]) if round_details else {}

    return {
        "match_id":      metadata.get("matchid", ""),
        "map":           map_name,
        "agent":         agent,
        "result":        "VICTOIRE" if won else "DÉFAITE",
        "rounds_played": rounds_played,
        "score_team":    f"{my_team.get('rounds_won',0)}-{my_team.get('rounds_lost',0)}",
        "kills":         kills_count,
        "deaths":        deaths_count,
        "assists":       assists_count,
        "kda":           round((kills_count + assists_count) / max(deaths_count, 1), 2),
        "hs_pct":        hs_pct,
        "damage_made":   me.get("damage_made", 0),
        "acs":           stats.get("score", 0) // max(rounds_played, 1),
        "spent_total":   spent_overall,
        "spent_avg":     spent_avg,
        "loadout_avg":   loadout_avg,
        "first_bloods":  first_bloods,
        "early_deaths":  early_deaths,
        "late_deaths":   late_deaths,
        "multi_kills":   multi_kills,
        "top_weapons":   top_weapons,
        "rank_in_team":  my_rank,
        "team_size":     len(team_players),
        "best_round":    best_round,
        "round_details": round_details,
        "total_rounds":  len(round_details),
    }

def build_match_prompt(detail: dict, player: str) -> str:
    won_rounds        = [r for r in detail["round_details"] if r["won"]]
    rounds_with_kills = [r for r in detail["round_details"] if r["kills"] > 0]
    rounds_0_kills    = [r for r in detail["round_details"] if r["kills"] == 0]

    multi_str = ""
    for n, count in detail["multi_kills"].items():
        if count > 0:
            multi_str += f"  - {count}x {n}K\n"

    weapons_str = "\n".join([f"  - {w}: {c} kills" for w, c in detail["top_weapons"]])

    rounds_str = ""
    for r in detail["round_details"]:
        icon = "✅" if r["won"] else "❌"
        rounds_str += f"  Round {r['round']:2d} {icon} : {r['kills']} kill(s)"
        if r["early_kills"]:
            rounds_str += f" dont {r['early_kills']} early"
        rounds_str += "\n"

    return f"""Tu es RiftIQ, un coach IA expert Valorant. Tu analyses une partie en détail.
Tu parles en français, avec un ton de coach professionnel et bienveillant.
Tu t'appuies UNIQUEMENT sur les données chiffrées fournies.
Ne cite JAMAIS de mécaniques d'agents spécifiques que tu ne connais pas avec certitude.
Sois très précis, cite les numéros de rounds et les chiffres exacts.

=== MATCH ANALYSÉ ===
Joueur  : {player}
Map     : {detail["map"]}
Agent   : {detail["agent"]}
Résultat: {detail["result"]} ({detail["score_team"]})

=== STATISTIQUES INDIVIDUELLES ===
K/D/A        : {detail["kills"]}/{detail["deaths"]}/{detail["assists"]} (KDA {detail["kda"]})
HS%          : {detail["hs_pct"]}%
ACS          : {detail["acs"]}
Dégâts       : {detail["damage_made"]}
Rang équipe  : #{detail["rank_in_team"]}/{detail["team_size"]}

=== ÉCONOMIE ===
Dépenses totales   : {detail["spent_total"]} crédits
Dépenses moyennes  : {detail["spent_avg"]} crédits/round
Valeur loadout moy : {detail["loadout_avg"]} crédits

=== MOMENTS CLÉS ===
First bloods   : {detail["first_bloods"]}
Morts early    : {detail["early_deaths"]} (avant 15s)
Morts late     : {detail["late_deaths"]} (après 60s)
Multi-kills    :
{multi_str if multi_str else "  Aucun multi-kill"}

=== ARMES ===
{weapons_str if weapons_str else "  Données indisponibles"}

=== DÉTAIL ROUND PAR ROUND ===
{rounds_str}
Rounds gagnés    : {len(won_rounds)}/{detail["total_rounds"]}
Rounds avec kill : {len(rounds_with_kills)}/{detail["total_rounds"]}
Rounds à 0 kill  : {len(rounds_0_kills)}/{detail["total_rounds"]}

=== CONSIGNES ===
1. Analyse l'impact individuel (rang équipe, KDA, dégâts)
2. Identifie les patterns round par round (séries de 0 kill, early deaths répétées)
3. Commente la gestion économique
4. Identifie 3 moments charnières de la partie
5. Donne 3 conseils CONCRETS basés uniquement sur ces chiffres
6. Ne cite PAS de mécaniques d'agents spécifiques
7. Encourage adapté au résultat ({detail["result"]})

=== GÉNÈRE L'ANALYSE ==="""

def ask_ollama_stream(prompt: str):
    payload = {
        "model":   OLLAMA_MODEL,
        "prompt":  prompt,
        "stream":  True,
        "options": {"temperature": 0.6, "top_p": 0.9, "num_predict": 1200}
    }
    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=180) as resp:
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break