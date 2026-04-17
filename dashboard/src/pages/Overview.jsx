import { useEffect, useState } from "react"

const C = { red:"#FF4655", cyan:"#00FFAA", gold:"#FFD700", grey:"#8A9BAA", bg3:"#1A2535" }

// ── Mini bar chart CSS ──────────────────────────────────────────────────────
function BarChart({ data, valueKey, labelKey, color = C.red, max }) {
  const m = max || Math.max(...data.map(d => d[valueKey] || 0), 1)
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
      {data.map((d, i) => (
        <div key={i} style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{ fontFamily:"var(--font-mono)", fontSize:11, color:C.grey, width:65, textAlign:"right", flexShrink:0 }}>
            {d[labelKey]}
          </div>
          <div style={{ flex:1, height:8, background:"var(--bg3)", borderRadius:2, overflow:"hidden" }}>
            <div style={{
              height:"100%", borderRadius:2,
              background: `linear-gradient(90deg, ${color}, ${color}88)`,
              width: `${Math.round((d[valueKey] || 0) / m * 100)}%`,
              transition: "width 0.8s ease"
            }}/>
          </div>
          <div style={{ fontFamily:"var(--font-mono)", fontSize:11, color:"var(--white)", width:36, textAlign:"right", flexShrink:0 }}>
            {typeof d[valueKey] === "number" && d[valueKey] % 1 !== 0 ? d[valueKey].toFixed(1) : d[valueKey]}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Line chart SVG ──────────────────────────────────────────────────────────
function LineChart({ data, keys, colors, height = 140 }) {
  if (!data.length) return null
  const w = 100 / (data.length - 1 || 1)

  return (
    <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none"
      style={{ width:"100%", height, display:"block" }}>
      {keys.map((key, ki) => {
        const vals = data.map(d => d[key] || 0)
        const max  = Math.max(...vals, 0.01)
        const min  = Math.min(...vals)
        const range = max - min || 1
        const pts   = vals.map((v, i) => `${i * w},${height - ((v - min) / range * (height - 10) + 5)}`).join(" ")
        return (
          <g key={ki}>
            <polyline points={pts} fill="none" stroke={colors[ki]} strokeWidth="1.5"
              strokeLinecap="round" strokeLinejoin="round"/>
            {vals.map((v, i) => (
              <circle key={i} cx={i * w} cy={height - ((v - min) / range * (height - 10) + 5)}
                r="2" fill={colors[ki]}/>
            ))}
          </g>
        )
      })}
    </svg>
  )
}

// ── Radar SVG ──────────────────────────────────────────────────────────────
function RadarChart({ data }) {
  const n = data.length
  const cx = 90, cy = 90, r = 70
  const angles = data.map((_, i) => (i / n) * 2 * Math.PI - Math.PI / 2)
  const pts = data.map((d, i) => ({
    x: cx + Math.cos(angles[i]) * r * (d.val / 100),
    y: cy + Math.sin(angles[i]) * r * (d.val / 100),
    lx: cx + Math.cos(angles[i]) * (r + 18),
    ly: cy + Math.sin(angles[i]) * (r + 18),
    label: d.stat,
    val: d.val
  }))
  const polyPts = pts.map(p => `${p.x},${p.y}`).join(" ")

  // Grilles
  const grids = [0.25, 0.5, 0.75, 1].map(scale => ({
    pts: data.map((_, i) => `${cx + Math.cos(angles[i]) * r * scale},${cy + Math.sin(angles[i]) * r * scale}`).join(" ")
  }))

  return (
    <svg viewBox="0 0 180 180" style={{ width:"100%", height:200 }}>
      {/* Grilles */}
      {grids.map((g, i) => (
        <polygon key={i} points={g.pts} fill="none" stroke="#1E2D3D" strokeWidth="0.5"/>
      ))}
      {/* Axes */}
      {data.map((_, i) => (
        <line key={i} x1={cx} y1={cy}
          x2={cx + Math.cos(angles[i]) * r}
          y2={cy + Math.sin(angles[i]) * r}
          stroke="#1E2D3D" strokeWidth="0.5"/>
      ))}
      {/* Données */}
      <polygon points={polyPts} fill={C.red + "33"} stroke={C.red} strokeWidth="1.5"/>
      {/* Labels */}
      {pts.map((p, i) => (
        <text key={i} x={p.lx} y={p.ly} textAnchor="middle" dominantBaseline="middle"
          fill={C.grey} fontSize="9" fontFamily="'Share Tech Mono'">
          {p.label}
        </text>
      ))}
    </svg>
  )
}

// ── KPI Box ─────────────────────────────────────────────────────────────────
function KPI({ label, value, color, sub }) {
  return (
    <div className="kpi animate-up" style={{ borderTop: `2px solid ${color}` }}>
      <div style={{ fontFamily:"var(--font-head)", fontSize:36, fontWeight:700, color, lineHeight:1, marginBottom:4 }}>
        {value}
      </div>
      <div style={{ fontFamily:"var(--font-mono)", fontSize:11, color:C.grey, letterSpacing:1, textTransform:"uppercase" }}>
        {label}
      </div>
      {sub && <div style={{ fontFamily:"var(--font-mono)", fontSize:10, color:C.grey, marginTop:2 }}>{sub}</div>}
    </div>
  )
}

// ── Overview principal ──────────────────────────────────────────────────────
export default function Overview({ matches, wins, total, avgKda, avgHs, avgAcs, winrate }) {

  // Agents
  const agentMap = {}
  matches.forEach(m => {
    if (!agentMap[m.agent]) agentMap[m.agent] = { wins:0, total:0, kda:0 }
    agentMap[m.agent].total++
    agentMap[m.agent].kda += m.kda
    if (m.won) agentMap[m.agent].wins++
  })
  const agents = Object.entries(agentMap)
    .map(([name, s]) => ({
      name, wr: Math.round(s.wins / s.total * 100),
      kda: +(s.kda / s.total).toFixed(2), games: s.total
    }))
    .sort((a, b) => b.games - a.games).slice(0, 6)

  // Maps
  const mapMap = {}
  matches.forEach(m => {
    const mp = m.map_name || "?"
    if (!mapMap[mp]) mapMap[mp] = { wins:0, total:0 }
    mapMap[mp].total++
    if (m.won) mapMap[mp].wins++
  })
  const maps = Object.entries(mapMap)
    .map(([name, s]) => ({ name, wr: Math.round(s.wins / s.total * 100), games: s.total }))
    .sort((a, b) => b.games - a.games)

  // Trend (chronologique)
  const trend = matches.slice().reverse().map((m, i) => ({
    i: i + 1, kda: +m.kda, hs: +m.headshot_pct, acs: m.acs
  }))

  const radarData = [
    { stat: "KDA",     val: Math.min(+avgKda / 3 * 100, 100) },
    { stat: "HS%",     val: Math.min(+avgHs / 40 * 100, 100) },
    { stat: "ACS",     val: Math.min(avgAcs / 300 * 100, 100) },
    { stat: "Winrate", val: winrate },
    { stat: "Impact",  val: Math.min(matches.reduce((s, m) => s + m.damage_made, 0) / total / 3000 * 100, 100) },
  ]

  const kdaColor = avgKda >= 1.5 ? C.cyan : avgKda >= 1.0 ? C.gold : C.red
  const wrColor  = winrate >= 55  ? C.cyan : winrate >= 45 ? C.gold : C.red

  return (
    <div>
      <div className="section-title">Vue d'ensemble</div>

      {/* KPIs */}
      <div className="kpi-grid" style={{ marginBottom:20 }}>
        <KPI label="Winrate"  value={`${winrate}%`} color={wrColor}/>
        <KPI label="KDA Moy." value={avgKda}         color={kdaColor}/>
        <KPI label="HS% Moy." value={`${avgHs}%`}   color={C.gold}/>
        <KPI label="ACS Moy." value={avgAcs}         color={C.cyan}/>
        <KPI label="Matchs"   value={total}          color={C.grey}/>
      </div>

      <div className="grid-2" style={{ marginBottom:16 }}>
        {/* KDA Evolution */}
        <div className="card">
          <div className="card-title">Évolution KDA</div>
          {trend.length > 1
            ? <LineChart data={trend} keys={["kda"]} colors={[C.red]} height={150}/>
            : <div style={{color:C.grey,fontFamily:"var(--font-mono)",fontSize:12,padding:"20px 0"}}>Pas assez de données</div>
          }
          <div style={{ display:"flex", gap:16, marginTop:8 }}>
            <span style={{ fontFamily:"var(--font-mono)", fontSize:10, color:C.red }}>● KDA</span>
          </div>
        </div>

        {/* Radar */}
        <div className="card">
          <div className="card-title">Profil joueur</div>
          <RadarChart data={radarData}/>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom:16 }}>
        {/* Agents */}
        <div className="card">
          <div className="card-title">Agents — Winrate</div>
          <BarChart data={agents} valueKey="wr" labelKey="name" color={C.red} max={100}/>
          <div style={{ marginTop:12 }}>
            <div className="card-title" style={{ marginBottom:8 }}>Agents — KDA</div>
            <BarChart data={agents} valueKey="kda" labelKey="name" color={C.cyan}/>
          </div>
        </div>

        {/* Maps */}
        <div className="card">
          <div className="card-title">Winrate par map</div>
          <BarChart data={maps} valueKey="wr" labelKey="name" color={C.gold} max={100}/>
        </div>
      </div>

      {/* ACS + HS% trend */}
      <div className="card">
        <div className="card-title">ACS & HS% par match</div>
        {trend.length > 1
          ? <LineChart data={trend} keys={["acs", "hs"]} colors={[C.cyan, C.gold]} height={140}/>
          : <div style={{color:C.grey,fontFamily:"var(--font-mono)",fontSize:12}}>Pas assez de données</div>
        }
        <div style={{ display:"flex", gap:16, marginTop:8 }}>
          <span style={{ fontFamily:"var(--font-mono)", fontSize:10, color:C.cyan }}>● ACS</span>
          <span style={{ fontFamily:"var(--font-mono)", fontSize:10, color:C.gold }}>● HS%</span>
        </div>
      </div>
    </div>
  )
}