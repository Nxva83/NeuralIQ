"""
RiftIQ — Module IA : Clustering K-Means + Heatmap v4
=====================================================
Améliorations v4 :
  - Couleur des points = DANGER (rouge = zone mortelle, vert = zone safe)
    indépendamment du cluster, basé sur la densité locale
  - KDE gaussien uniquement dans les zones de la map (masque alpha)
  - Minimap bien lumineuse avec fond sombre pour faire ressortir les couleurs
  - Labels repositionnés proprement, jamais sur les croix
  - Effet de chaleur bien visible

Usage:
    python heatmap.py --name "TonPseudo" --tag "EUW"
"""

import os, argparse, requests, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap, Normalize
from scipy.ndimage import gaussian_filter
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter

# ─── Config ────────────────────────────────────────────────────────────────────

HENRIK_API_KEY = os.getenv("HENRIK_API_KEY", "")
HENRIK_HEADERS = {"Authorization": HENRIK_API_KEY, "User-Agent": "RiftIQ/1.0"}
OUTPUT_DIR     = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
IMG_SIZE = 1024

# ─── Paramètres officiels valorant-api.com ─────────────────────────────────────

MAP_PARAMS = {
    "Ascent":   {"xMult": 7e-05,   "yMult": -7e-05,   "xAdd": 0.813895, "yAdd": 0.573242,
                 "icon": "https://media.valorant-api.com/maps/7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/displayicon.png"},
    "Split":    {"xMult": 7.8e-05, "yMult": -7.8e-05, "xAdd": 0.842188, "yAdd": 0.697578,
                 "icon": "https://media.valorant-api.com/maps/d960549e-485c-e861-8d71-aa9d1aed12a2/displayicon.png"},
    "Fracture": {"xMult": 7.8e-05, "yMult": -7.8e-05, "xAdd": 0.556952, "yAdd": 1.155886,
                 "icon": "https://media.valorant-api.com/maps/b529448b-4d60-346e-e89e-00a4c527a405/displayicon.png"},
    "Bind":     {"xMult": 5.9e-05, "yMult": -5.9e-05, "xAdd": 0.576941, "yAdd": 0.967566,
                 "icon": "https://media.valorant-api.com/maps/2c9d57ec-4431-9c5e-2939-8f9ef6dd5cba/displayicon.png"},
    "Breeze":   {"xMult": 7e-05,   "yMult": -7e-05,   "xAdd": 0.465123, "yAdd": 0.833078,
                 "icon": "https://media.valorant-api.com/maps/2fb9a4fd-47b8-4e7d-a969-74b4046ebd53/displayicon.png"},
    "Icebox":   {"xMult": 7.2e-05, "yMult": -7.2e-05, "xAdd": 0.460214, "yAdd": 0.304687,
                 "icon": "https://media.valorant-api.com/maps/e2ad5c54-4114-a870-9641-8ea21279579a/displayicon.png"},
    "Haven":    {"xMult": 7.5e-05, "yMult": -7.5e-05, "xAdd": 1.09345,  "yAdd": 0.642728,
                 "icon": "https://media.valorant-api.com/maps/2bee0dc9-4ffe-519b-1cbd-7fbe763a6047/displayicon.png"},
    "Pearl":    {"xMult": 7.8e-05, "yMult": -7.8e-05, "xAdd": 0.480469, "yAdd": 0.916016,
                 "icon": "https://media.valorant-api.com/maps/fd267378-4d1d-484f-ff52-77821ed10dc2/displayicon.png"},
    "Lotus":    {"xMult": 7.2e-05, "yMult": -7.2e-05, "xAdd": 0.454789, "yAdd": 0.917752,
                 "icon": "https://media.valorant-api.com/maps/2fe4ed3a-450a-948b-6d6b-e89a78e680a9/displayicon.png"},
    "Sunset":   {"xMult": 7.8e-05, "yMult": -7.8e-05, "xAdd": 0.5,      "yAdd": 0.515625,
                 "icon": "https://media.valorant-api.com/maps/92584fbe-486a-b1b2-9faa-39b0f486b498/displayicon.png"},
    "Abyss":    {"xMult": 8.1e-05, "yMult": -8.1e-05, "xAdd": 0.5,      "yAdd": 0.5,
                 "icon": "https://media.valorant-api.com/maps/224b0a95-48b9-f703-1bd8-67aca101a61f/displayicon.png"},
    "Corrode":  {"xMult": 7e-05,   "yMult": -7e-05,   "xAdd": 0.526158, "yAdd": 0.5,
                 "icon": "https://media.valorant-api.com/maps/1c18ab1f-420d-0d8b-71d0-77ad3c439115/displayicon.png"},
}

# Palette danger : vert (safe) → jaune → rouge (dangereux)
DANGER_CMAP = LinearSegmentedColormap.from_list(
    "danger", ["#00FF88", "#FFD700", "#FF4555"], N=256
)
# KDE morts : transparent → rouge vif
KDE_DEATH_CMAP = LinearSegmentedColormap.from_list(
    "kde_death", ["#00000000", "#FF000033", "#FF4555BB", "#FF0000EE"], N=256
)
# KDE kills : transparent → vert vif
KDE_KILL_CMAP = LinearSegmentedColormap.from_list(
    "kde_kill", ["#00000000", "#00FF8833", "#00FFAAAA", "#00FF88EE"], N=256
)

# ─── Conversion coordonnées ────────────────────────────────────────────────────

def game_to_pixel(gx, gy, map_name):
    p = MAP_PARAMS.get(map_name)
    if not p:
        return None, None
    rx = gy * p["xMult"] + p["xAdd"]
    ry = gx * p["yMult"] + p["yAdd"]
    if not (-0.05 <= rx <= 1.05 and -0.05 <= ry <= 1.05):
        return None, None
    return max(0., min(1., rx)) * IMG_SIZE, max(0., min(1., ry)) * IMG_SIZE

# ─── KDE gaussien ──────────────────────────────────────────────────────────────

def make_kde(pixels, sigma=32.0):
    grid = np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.float32)
    for px, py in pixels:
        xi = int(np.clip(px, 0, IMG_SIZE - 1))
        yi = int(np.clip(py, 0, IMG_SIZE - 1))
        grid[yi, xi] += 1.0
    kde = gaussian_filter(grid, sigma=sigma)
    if kde.max() > 0:
        kde /= kde.max()
    return kde

# ─── Masque alpha de la minimap ────────────────────────────────────────────────

def get_map_mask(minimap_rgba: np.ndarray) -> np.ndarray:
    """
    Extrait le masque de la map depuis le canal alpha de la minimap.
    Les zones transparentes (hors map) sont masquées.
    """
    if minimap_rgba.shape[2] == 4:
        alpha = minimap_rgba[:, :, 3].astype(np.float32) / 255.0
        # Seuil : pixel considéré "dans la map" si alpha > 10%
        mask = (alpha > 0.1).astype(np.float32)
        # Dilate légèrement le masque pour inclure les bords
        mask = gaussian_filter(mask, sigma=3) > 0.3
        return mask.astype(np.float32)
    return np.ones((IMG_SIZE, IMG_SIZE), dtype=np.float32)

# ─── K-Means ───────────────────────────────────────────────────────────────────

def optimal_k(n):
    if n < 4:  return 1
    if n < 10: return 2
    if n < 20: return 3
    if n < 35: return 4
    return 5

def cluster(pixels, k):
    arr    = np.array(pixels)
    sc     = StandardScaler()
    scaled = sc.fit_transform(arr)
    km     = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(scaled)
    centers = sc.inverse_transform(km.cluster_centers_)
    sizes   = {i: int(np.sum(labels == i)) for i in range(k)}
    return {"labels": labels, "centers": centers, "sizes": sizes, "arr": arr}

# ─── Minimap ───────────────────────────────────────────────────────────────────

def fetch_minimap(map_name):
    url = MAP_PARAMS.get(map_name, {}).get("icon")
    if not url:
        return None, None
    try:
        r = requests.get(url, timeout=10)
        if r.ok:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            # Améliore la lisibilité
            rgb = img.convert("RGB")
            rgb = ImageEnhance.Brightness(rgb).enhance(1.5)
            rgb = ImageEnhance.Contrast(rgb).enhance(1.4)
            rgb = ImageEnhance.Color(rgb).enhance(1.3)
            final = rgb.convert("RGBA")
            # Récupère alpha original pour le masque
            original_alpha = img.split()[3]
            final.putalpha(original_alpha)
            arr = np.array(final)
            mask = get_map_mask(arr)
            return final, mask
    except Exception as e:
        print(f"  ⚠️  Minimap : {e}")
    return None, None

# ─── Densité locale par point ──────────────────────────────────────────────────

def local_density(pixels, kde_grid):
    """
    Pour chaque point, récupère sa valeur de densité KDE locale.
    Utilisé pour colorier les points : rouge = zone dense = dangereuse.
    """
    densities = []
    for px, py in pixels:
        xi = int(np.clip(px, 0, IMG_SIZE - 1))
        yi = int(np.clip(py, 0, IMG_SIZE - 1))
        densities.append(kde_grid[yi, xi])
    return np.array(densities)

# ─── Labels ────────────────────────────────────────────────────────────────────

def place_label(ax, cx, cy, text, color_accent, color_bg, used, offset=60):
    candidates = [
        (cx,          cy - offset,  "center", "bottom"),
        (cx,          cy + offset,  "center", "top"),
        (cx - offset, cy,           "right",  "center"),
        (cx + offset, cy,           "left",   "center"),
        (cx - offset, cy - offset,  "right",  "bottom"),
        (cx + offset, cy - offset,  "left",   "bottom"),
        (cx + offset, cy + offset,  "left",   "top"),
        (cx - offset, cy + offset,  "right",  "top"),
    ]
    best = None
    for lx, ly, ha, va in candidates:
        lx = max(90, min(IMG_SIZE - 90, lx))
        ly = max(22, min(IMG_SIZE - 22, ly))
        too_close = any(abs(lx - ux) < 130 and abs(ly - uy) < 40
                        for ux, uy in used)
        if not too_close:
            best = (lx, ly, ha, va)
            break
    if best is None:
        lx = max(90, min(IMG_SIZE - 90, candidates[0][0]))
        ly = max(22, min(IMG_SIZE - 22, candidates[0][1]))
        best = (lx, ly, candidates[0][2], candidates[0][3])

    lx, ly, ha, va = best
    used.append((lx, ly))
    ax.annotate("", xy=(cx, cy), xytext=(lx, ly),
                arrowprops=dict(arrowstyle="-", color=color_accent,
                                lw=1.2, alpha=0.7), zorder=7)
    ax.text(lx, ly, text, color="white", fontsize=9, fontweight="bold",
            ha=ha, va=va, zorder=9,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=color_bg,
                      edgecolor=color_accent, linewidth=1.5, alpha=0.95),
            path_effects=[pe.withStroke(linewidth=1, foreground="#000")])

# ─── Génération heatmap ────────────────────────────────────────────────────────

def generate_heatmap(events, map_name, event_type, player, out_path):
    pixels = []
    for ev in events:
        px, py = game_to_pixel(ev["x"], ev["y"], map_name)
        if px is not None:
            pixels.append((px, py))
    if not pixels:
        print(f"  ⚠️  Aucun point valide : {map_name} {event_type}")
        return
    print(f"  🖼️  {map_name} {event_type} : {len(pixels)} pts")

    k       = optimal_k(len(pixels))
    res     = cluster(pixels, k)
    labels  = res["labels"]
    centers = res["centers"]
    sizes   = res["sizes"]
    arr     = res["arr"]

    # KDE
    kde      = make_kde(pixels, sigma=30)
    kde_cmap = KDE_DEATH_CMAP if event_type == "death" else KDE_KILL_CMAP

    # Couleur des points = densité locale (danger)
    densities  = local_density(pixels, kde)
    norm_dens  = Normalize(vmin=0, vmax=max(densities.max(), 0.01))
    point_colors = DANGER_CMAP(norm_dens(densities))

    # Minimap
    minimap_img, map_mask = fetch_minimap(map_name)

    # ── Figure ──────────────────────────────────────────────────────────────────
    is_death  = event_type == "death"
    accent    = "#FF4555" if is_death else "#00FFAA"
    bg_label  = "#2D0008" if is_death else "#002D1A"
    title_c   = "#FF6677" if is_death else "#00FFAA"

    fig, ax = plt.subplots(figsize=(11, 11), dpi=130)
    fig.patch.set_facecolor("#080F18")
    ax.set_xlim(0, IMG_SIZE)
    ax.set_ylim(IMG_SIZE, 0)
    ax.set_aspect("equal")
    ax.axis("off")

    # Bordure colorée
    rect = plt.Rectangle((0, 0), IMG_SIZE, IMG_SIZE,
                          fill=False, edgecolor=accent, lw=3, zorder=10)
    ax.add_patch(rect)

    # ── 1. Minimap ──────────────────────────────────────────────────────────────
    if minimap_img:
        ax.imshow(np.array(minimap_img),
                  extent=[0, IMG_SIZE, IMG_SIZE, 0],
                  origin="upper", alpha=0.82, zorder=0)
    else:
        ax.set_facecolor("#1A2535")

    # ── 2. KDE masqué par la géographie de la map ───────────────────────────────
    kde_display = kde.copy()
    if map_mask is not None:
        # On applique le masque : hors map = 0
        kde_display = kde_display * map_mask
    # Seuil bas pour ne montrer que les zones significatives
    kde_masked = np.where(kde_display > 0.08, kde_display, np.nan)
    ax.imshow(kde_masked,
              cmap=kde_cmap,
              extent=[0, IMG_SIZE, IMG_SIZE, 0],
              origin="upper", alpha=0.80, zorder=2,
              interpolation="bilinear",
              vmin=0.08, vmax=1.0)

    # ── 3. Points colorés par DENSITÉ (rouge = danger, vert = safe) ─────────────
    point_sizes = np.array([55 + sizes[l] * 7 for l in labels])
    scatter = ax.scatter(arr[:, 0], arr[:, 1],
                         c=densities, cmap=DANGER_CMAP,
                         norm=norm_dens,
                         s=point_sizes, alpha=0.90, zorder=4,
                         edgecolors="white", linewidths=0.7)

    # ── 4. Croix des centres ────────────────────────────────────────────────────
    sorted_clusters = sorted(sizes.items(), key=lambda x: x[1], reverse=True)
    for i, sz in sorted_clusters:
        cx, cy = centers[i]
        # Couleur de la croix = danger du cluster
        d_val = local_density([(cx, cy)], kde)[0]
        cross_c = matplotlib.colors.to_hex(DANGER_CMAP(norm_dens(d_val)))
        ax.plot(cx, cy, marker="X", color=cross_c,
                markersize=16, zorder=6,
                markeredgecolor="white", markeredgewidth=2.2)

    # ── 5. Labels ───────────────────────────────────────────────────────────────
    used = []
    for rank, (i, sz) in enumerate(sorted_clusters):
        cx, cy  = centers[i]
        pct     = round(sz / len(pixels) * 100)
        d_val   = local_density([(cx, cy)], kde)[0]
        danger  = int(d_val * 100)

        if rank == 0:
            txt = f"⚠️  Zone {i+1}\n{sz} pts · {pct}% · danger {danger}%"
            bg  = "#3D0010" if is_death else "#003D22"
        else:
            txt = f"Zone {i+1}  {sz} pts"
            bg  = bg_label
        place_label(ax, cx, cy, txt, accent, bg, used)

    # ── 6. Légende couleur ──────────────────────────────────────────────────────
    ax.set_title(
        f"{'💀' if is_death else '🎯'}  {player}  —  "
        f"{'MORTS' if is_death else 'KILLS'} sur {map_name}\n"
        f"K-Means · {k} zones · {len(pixels)} événements  "
        f"{'🔴 Rouge = zone mortelle  🟢 Vert = zone safe' if is_death else '🔴 Rouge = zone active  🟢 Vert = zone sporadique'}",
        color=title_c, fontsize=12, fontweight="bold", pad=16,
        path_effects=[pe.withStroke(linewidth=2, foreground="#080F18")]
    )

    # Barre de danger
    ax_cb = fig.add_axes([0.12, 0.025, 0.76, 0.016])
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    ax_cb.imshow(gradient, aspect="auto", cmap=DANGER_CMAP)
    ax_cb.set_xticks([0, 128, 255])
    ax_cb.set_xticklabels(["🟢 Safe", "⚠️  Modéré", "🔴 Danger"],
                           color="#CCDDEE", fontsize=9)
    ax_cb.set_yticks([])
    for sp in ax_cb.spines.values():
        sp.set_edgecolor(accent)
        sp.set_linewidth(1)

    ax.text(0.995, 0.005, "RiftIQ — Pro Edition",
            transform=ax.transAxes, color="#445566",
            fontsize=8, ha="right", va="bottom")

    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#080F18")
    plt.close()
    print(f"  💾 {out_path}")

# ─── Fetch events ──────────────────────────────────────────────────────────────

def fetch_events(game_name, tag_line, region="eu", count=20):
    print(f"📡 Récupération des matchs pour {game_name}#{tag_line}...")
    url = (f"https://api.henrikdev.xyz/valorant/v3/matches"
           f"/{region}/{game_name}/{tag_line}"
           f"?mode=competitive&size={min(count, 20)}")
    resp = requests.get(url, headers=HENRIK_HEADERS)
    if resp.status_code == 429:
        print("  ⚠️  Rate limit, pause 12s...")
        time.sleep(12)
        return fetch_events(game_name, tag_line, region, count)
    if not resp.ok:
        raise RuntimeError(f"Henrik {resp.status_code}: {resp.text[:150]}")
    matches = resp.json().get("data", [])
    print(f"  ✅ {len(matches)} matchs")
    my_id  = f"{game_name}#{tag_line}".lower()
    events = []
    for match in matches:
        map_name = match.get("metadata", {}).get("map", "Unknown")
        for kill in match.get("kills", []):
            killer = (kill.get("killer_display_name") or "").lower()
            victim = (kill.get("victim_display_name") or "").lower()
            vloc   = kill.get("victim_death_location") or {}
            vx, vy = vloc.get("x"), vloc.get("y")
            if vx is None or vy is None:
                continue
            weapon = kill.get("damage_weapon_name", "Unknown")
            if victim == my_id:
                events.append({"map": map_name, "x": vx, "y": vy,
                                "type": "death", "weapon": weapon})
            if killer == my_id:
                events.append({"map": map_name, "x": vx, "y": vy,
                                "type": "kill", "weapon": weapon})
    kills  = sum(1 for e in events if e["type"] == "kill")
    deaths = sum(1 for e in events if e["type"] == "death")
    print(f"  🎯 {kills} kills  |  💀 {deaths} morts\n")
    return events

# ─── Rapport ───────────────────────────────────────────────────────────────────

def generate_report(kills_by_map, deaths_by_map, player):
    lines = [
        "╔══════════════════════════════════════════════╗",
        f"  🗺️  Rapport de zones — {player}",
        "╚══════════════════════════════════════════════╝", "",
    ]
    for map_name in sorted(set(kills_by_map) | set(deaths_by_map)):
        k_evs = kills_by_map.get(map_name, [])
        d_evs = deaths_by_map.get(map_name, [])
        lines.append(f"──── 🗺️  {map_name}  ({len(k_evs)} kills, {len(d_evs)} morts)")
        d_px = [(px, py) for ev in d_evs
                for px, py in [game_to_pixel(ev["x"], ev["y"], map_name)]
                if px is not None]
        if d_px:
            kde = make_kde(d_px)
            k   = optimal_k(len(d_px))
            res = cluster(d_px, k)
            top = max(res["sizes"].items(), key=lambda x: x[1])
            pct = round(top[1] / len(d_px) * 100)
            cx, cy = res["centers"][top[0]]
            danger = int(local_density([(cx, cy)], kde)[0] * 100)
            lines.append(f"  💀 Zone de mort principale : {top[1]} morts ({pct}%) · danger {danger}%")
            if pct > 50:
                lines.append(f"  ⚠️  POINT NOIR : change ton positionnement sur {map_name} !")
            else:
                lines.append(f"  ✅  Morts bien réparties.")
        lines.append("")
    return "\n".join(lines)

# ─── Main ──────────────────────────────────────────────────────────────────────

def run(game_name, tag_line, region="eu", count=20):
    print("\n" + "═" * 50)
    print("  🧠 RiftIQ — K-Means Heatmap v4")
    print("═" * 50 + "\n")

    events = fetch_events(game_name, tag_line, region, count)
    if not events:
        print("❌ Aucun événement.")
        return

    kills_by_map  = defaultdict(list)
    deaths_by_map = defaultdict(list)
    for ev in events:
        (kills_by_map if ev["type"] == "kill" else deaths_by_map)[ev["map"]].append(ev)

    print("🖼️  Génération des heatmaps...\n")
    player = f"{game_name}#{tag_line}"

    for map_name in sorted(set(kills_by_map) | set(deaths_by_map)):
        if map_name not in MAP_PARAMS:
            print(f"  ⏭️  {map_name} ignorée")
            continue
        if kills_by_map.get(map_name):
            generate_heatmap(kills_by_map[map_name], map_name, "kill", player,
                             os.path.join(OUTPUT_DIR, f"heatmap_{map_name}_kills.png"))
        if deaths_by_map.get(map_name):
            generate_heatmap(deaths_by_map[map_name], map_name, "death", player,
                             os.path.join(OUTPUT_DIR, f"heatmap_{map_name}_deaths.png"))

    report = generate_report(kills_by_map, deaths_by_map, player)
    print("\n" + report)
    rpath = os.path.join(OUTPUT_DIR, f"rapport_{game_name}_{tag_line}.txt")
    with open(rpath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  ✅ Images dans : {OUTPUT_DIR}/")
    print(f"  👉 explorer.exe {OUTPUT_DIR}/\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name",    required=True)
    parser.add_argument("--tag",     required=True)
    parser.add_argument("--region",  default="eu")
    parser.add_argument("--matches", default=20, type=int)
    args = parser.parse_args()
    run(args.name, args.tag, args.region, args.matches)