"""
RiftIQ — Pipeline de données Valorant
======================================
Utilise :
  - Riot API officielle  → PUUID du joueur
  - Henrik Dev API       → historique et détail des matchs

Usage:
    python riot_pipeline.py --name "TonPseudo" --tag "EUW" --matches 20
"""

import os
import time
import json
import argparse
import requests
from dataclasses import dataclass, asdict
from typing import Optional

# ─── Config ────────────────────────────────────────────────────────────────────

API_KEY        = os.getenv("RIOT_API_KEY",   "RGAPI-xxxx")
HENRIK_API_KEY = os.getenv("HENRIK_API_KEY", "")

REGIONS = {
    "euw": {"platform": "euw1", "region": "europe", "henrik_region": "eu"},
    "na":  {"platform": "na1",  "region": "americas", "henrik_region": "na"},
    "kr":  {"platform": "kr",   "region": "asia",     "henrik_region": "kr"},
}

RIOT_HEADERS   = {"X-Riot-Token": API_KEY}
HENRIK_HEADERS = {"User-Agent": "RiftIQ-EIP/1.0", "Authorization": HENRIK_API_KEY}
RATE_LIMIT_PAUSE = 1.2

# ─── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PlayerInfo:
    puuid: str
    game_name: str
    tag_line: str
    region: str

@dataclass
class MatchSummary:
    match_id: str
    game_start: str
    duration_seconds: int
    map_name: str
    mode: str
    won: bool
    agent: str
    kills: int
    deaths: int
    assists: int
    kda: float
    headshot_pct: float
    damage_made: int
    damage_received: int
    economy_score: int
    acs: int
    first_bloods: int

@dataclass
class RoundEvent:
    round_number: int
    event_type: str
    timestamp_ms: int
    weapon: Optional[str]
    position_x: Optional[float]
    position_y: Optional[float]
    headshot: bool

# ─── Client ────────────────────────────────────────────────────────────────────

class RiotClient:
    def __init__(self, region: str = "euw"):
        cfg = REGIONS[region]
        self.platform      = cfg["platform"]
        self.region        = cfg["region"]
        self.henrik_region = cfg["henrik_region"]
        self.game_name     = ""
        self.tag_line      = ""
        self._last_call    = 0.0

    def _riot_get(self, url: str) -> dict:
        elapsed = time.time() - self._last_call
        if elapsed < RATE_LIMIT_PAUSE:
            time.sleep(RATE_LIMIT_PAUSE - elapsed)
        resp = requests.get(url, headers=RIOT_HEADERS)
        self._last_call = time.time()
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 10))
            print(f"  ⚠️  Rate limit Riot — pause {wait}s...")
            time.sleep(wait)
            return self._riot_get(url)
        if not resp.ok:
            raise RuntimeError(f"Riot API {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def _henrik_get(self, url: str) -> dict:
        resp = requests.get(url, headers=HENRIK_HEADERS)
        if resp.status_code == 429:
            print("  ⚠️  Rate limit Henrik — pause 12s...")
            time.sleep(12)
            return self._henrik_get(url)
        if not resp.ok:
            raise RuntimeError(f"Henrik API {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    # ── Joueur ────────────────────────────────────────────────────────────────

    def get_player(self, game_name: str, tag_line: str) -> PlayerInfo:
        print(f"🔍 Recherche du compte {game_name}#{tag_line}...")
        self.game_name = game_name
        self.tag_line  = tag_line
        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        )
        data  = self._riot_get(url)
        puuid = data["puuid"]
        print(f"  ✅ PUUID Riot : {puuid[:24]}...")
        return PlayerInfo(puuid=puuid, game_name=game_name,
                          tag_line=tag_line, region=self.region)

    # ── Matchs ────────────────────────────────────────────────────────────────

    def get_match_ids(self, count: int = 20, queue: str = "competitive") -> list[str]:
        """
        Récupère les match IDs via deux endpoints Henrik :
        1. stored-matches — historique complet stocké par Henrik
        2. v3/matches — fallback sur les matchs récents si stored vide
        """
        ids  = []
        page = 0

        # ── Tentative 1 : stored-matches (historique complet) ──
        print("  🔍 Récupération via stored-matches...")
        while len(ids) < count:
            batch = min(20, count - len(ids))
            url   = (
                f"https://api.henrikdev.xyz/valorant/v1/stored-matches"
                f"/{self.henrik_region}/{self.game_name}/{self.tag_line}"
                f"?mode={queue}&size={batch}&page={page}"
            )
            try:
                data    = self._henrik_get(url)
                matches = data.get("data", [])
                if not matches:
                    break
                # stored-matches utilise meta.id au lieu de metadata.matchid
                new_ids = []
                for m in matches:
                    mid = (m.get("meta") or {}).get("id") or                           (m.get("metadata") or {}).get("matchid") or                           m.get("matchId") or m.get("match_id")
                    if mid:
                        new_ids.append(mid)
                if not new_ids:
                    break
                ids += new_ids
                print(f"  📋 stored page {page+1} : {len(new_ids)} matchs (total : {len(ids)})")
                page += 1
                if len(matches) < batch:
                    break
                time.sleep(1.5)
            except Exception as e:
                print(f"  ⚠️  stored-matches erreur : {e}")
                break

        # ── Tentative 2 : v3/matches (fallback si stored vide) ──
        if not ids:
            print("  🔍 Fallback sur v3/matches...")
            page = 0
            while len(ids) < count:
                batch = min(20, count - len(ids))
                url   = (
                    f"https://api.henrikdev.xyz/valorant/v3/matches"
                    f"/{self.henrik_region}/{self.game_name}/{self.tag_line}"
                    f"?mode={queue}&size={batch}&page={page}"
                )
                data    = self._henrik_get(url)
                matches = data.get("data", [])
                if not matches:
                    break
                ids += [m["metadata"]["matchid"] for m in matches]
                print(f"  📋 v3 page {page+1} : {len(matches)} matchs (total : {len(ids)})")
                page += 1
                if len(matches) < batch:
                    break
                time.sleep(1.5)

        print(f"  ✅ {len(ids)} matchs récupérés au total")
        return ids

    def get_match_detail(self, match_id: str) -> dict:
        url = f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}"
        return self._henrik_get(url).get("data", {})

    # ── Parsing ───────────────────────────────────────────────────────────────

    def parse_match(self, raw: dict, game_name: str, tag_line: str) -> tuple:
        """
        Parse un match Henrik v2.
        Matching par name+tag car le PUUID Henrik != PUUID Riot.
        """
        metadata    = raw.get("metadata", {})
        all_players = raw.get("players", {}).get("all_players", [])
        rounds      = raw.get("rounds", [])

        # ✅ Matching fiable par name+tag (insensible à la casse)
        me = next((
            p for p in all_players
            if p.get("name", "").lower() == game_name.lower()
            and p.get("tag",  "").lower() == tag_line.lower()
        ), None)

        if me is None:
            # Dernier recours : on affiche les joueurs pour debug
            names = [(p.get("name"), p.get("tag")) for p in all_players]
            raise ValueError(
                f"Joueur {game_name}#{tag_line} introuvable.\n"
                f"Joueurs dans le match : {names}"
            )

        stats   = me.get("stats", {})
        team_id = me.get("team", "").lower()   # "red" ou "blue"
        teams   = raw.get("teams", {})
        won     = teams.get(team_id, {}).get("has_won", False)

        k   = stats.get("kills",   0)
        d   = stats.get("deaths",  0)
        a   = stats.get("assists", 0)
        kda = round((k + a) / max(d, 1), 2)

        hs    = stats.get("headshots", 0)
        bs    = stats.get("bodyshots", 0)
        ls    = stats.get("legshots",  0)
        total = hs + bs + ls
        hs_pct = round(hs / total * 100, 1) if total > 0 else 0.0

        spent         = me.get("economy", {}).get("spent", {}).get("overall", 0)
        rounds_played = max(metadata.get("rounds_played", 1), 1)

        summary = MatchSummary(
            match_id=metadata.get("matchid", ""),
            game_start=metadata.get("game_start_patched", ""),
            duration_seconds=metadata.get("game_length", 0),
            map_name=metadata.get("map", ""),
            mode=metadata.get("mode", ""),
            won=won,
            agent=me.get("character", ""),
            kills=k, deaths=d, assists=a, kda=kda,
            headshot_pct=hs_pct,
            damage_made=me.get("damage_made", 0),
            damage_received=me.get("damage_received", 0),
            economy_score=spent,
            acs=stats.get("score", 0) // rounds_played,
            first_bloods=stats.get("first_bloods", 0),
        )

        # Évènements de kills par round
        events = []
        for rnd in rounds:
            for pstat in rnd.get("player_stats", []):
                # Matching par name dans les rounds aussi
                if (pstat.get("player_display_name", "").lower()
                        != f"{game_name}#{tag_line}".lower()
                    and pstat.get("player_puuid") != me.get("puuid")):
                    continue
                for kill in pstat.get("kill_events", []):
                    loc = kill.get("victim_death_location", {})
                    fd  = kill.get("finishing_damage", {})
                    events.append(RoundEvent(
                        round_number=rnd.get("round_num", 0),
                        event_type="kill",
                        timestamp_ms=kill.get("kill_time_in_round", 0),
                        weapon=fd.get("damage_type", ""),
                        position_x=loc.get("x"),
                        position_y=loc.get("y"),
                        headshot=fd.get("damage_item", "") == "Primary",
                    ))

        return summary, events


# ─── Pipeline ──────────────────────────────────────────────────────────────────

class RiftIQPipeline:
    def __init__(self, region: str = "euw"):
        self.client   = RiotClient(region)
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    def run(self, game_name: str, tag_line: str, match_count: int = 20):
        print("\n" + "═" * 50)
        print("  🎮 RiftIQ — Pipeline de données Valorant")
        print("═" * 50 + "\n")

        # 1. Récupère le joueur via Riot API (PUUID officiel)
        player = self.client.get_player(game_name, tag_line)
        self._save(f"player_{game_name}_{tag_line}.json", asdict(player))

        # 2. IDs de matchs via Henrik (par name/tag)
        print(f"\n📥 Récupération des {match_count} derniers matchs compétitifs...")
        match_ids = self.client.get_match_ids(count=match_count)

        # 3. Fetch + parse chaque match
        summaries, all_events = [], []
        for i, match_id in enumerate(match_ids, 1):
            print(f"\n  [{i}/{len(match_ids)}] {match_id[:20]}...")
            try:
                raw = self.client.get_match_detail(match_id)
                summary, events = self.client.parse_match(raw, game_name, tag_line)
                summaries.append(asdict(summary))
                all_events.extend([asdict(e) for e in events])

                result = "✅ WIN" if summary.won else "❌ LOSS"
                print(
                    f"    {result} · {summary.agent:15} · "
                    f"K/D/A {summary.kills}/{summary.deaths}/{summary.assists} · "
                    f"HS% {summary.headshot_pct}% · ACS {summary.acs}"
                )
                time.sleep(0.5)
            except Exception as e:
                print(f"    ⚠️  Erreur : {e}")
                continue

        # 4. Sauvegarde
        self._save(f"matches_{game_name}_{tag_line}.json", summaries)
        self._save(f"events_{game_name}_{tag_line}.json",  all_events)

        # 5. Résumé
        self._print_stats(summaries, game_name, tag_line)

    def _save(self, filename, data):
        path = os.path.join(self.data_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 {path}")

    def _print_stats(self, summaries, name, tag):
        if not summaries:
            print("\n  ⚠️  Aucun match analysé.")
            return
        from collections import Counter
        total   = len(summaries)
        wins    = sum(1 for m in summaries if m["won"])
        avg_kda = round(sum(m["kda"] for m in summaries) / total, 2)
        avg_hs  = round(sum(m["headshot_pct"] for m in summaries) / total, 1)
        avg_acs = round(sum(m["acs"] for m in summaries) / total)
        top     = Counter(m["agent"] for m in summaries).most_common(1)[0]

        print("\n" + "─" * 50)
        print(f"  📊 Résumé — {name}#{tag}")
        print("─" * 50)
        print(f"  Matchs   : {total}")
        print(f"  Winrate  : {wins}/{total} ({round(wins/total*100)}%)")
        print(f"  KDA moy. : {avg_kda}")
        print(f"  HS%      : {avg_hs}%")
        print(f"  ACS      : {avg_acs}")
        print(f"  Agent ❤️  : {top[0]} ({top[1]} matchs)")
        print("─" * 50)
        print(f"\n  ✅ Lance : python analyze.py --name \"{name}\" --tag \"{tag}\"\n")


# ─── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RiftIQ — Riot Data Pipeline")
    parser.add_argument("--name",    required=True)
    parser.add_argument("--tag",     required=True)
    parser.add_argument("--region",  default="euw", choices=REGIONS.keys())
    parser.add_argument("--matches", default=20, type=int)
    args = parser.parse_args()
    RiftIQPipeline(region=args.region).run(args.name, args.tag, args.matches)