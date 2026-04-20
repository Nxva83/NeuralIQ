import { useState, useEffect } from "react"
import './index.css'
import Overview from "./pages/Overview"
import Matches from "./pages/Matches"
import Heatmaps from "./pages/Heatmaps"
import Report from "./pages/Report"
import Coach from "./pages/Coach"
import MatchAnalysis from "./pages/MatchAnalysis"
import VideoCoach from "./pages/VideoCoach"

const PLAYER = { name: "TuOrdinateur", tag: "6969" }
const API = "http://localhost:8000"

const NAV = [
  { id: "overview",  icon: "📊", label: "Overview"      },
  { id: "matches",   icon: "🎮", label: "Matches"       },
  { id: "heatmaps",  icon: "🗺️", label: "Heatmaps"      },
  { id: "report",    icon: "📝", label: "Rapport"       },
  { id: "coach",     icon: "🤖", label: "Coach IA"      },
  { id: "analysis",  icon: "🔬", label: "Analyse Match" },
  { id: "video",     icon: "🎬", label: "Coach Vidéo"   },
]

export default function App() {
  const [page, setPage]           = useState("overview")
  const [matches, setMatches]     = useState([])
  const [heatmaps, setHeatmaps]   = useState({})
  const [report, setReport]       = useState("")
  const [loading, setLoading]     = useState(true)
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`${API}/api/matches/${PLAYER.name}/${PLAYER.tag}`).then(r => r.json()),
      fetch(`${API}/api/heatmaps/${PLAYER.name}/${PLAYER.tag}`).then(r => r.json()),
      fetch(`${API}/api/report/${PLAYER.name}/${PLAYER.tag}`).then(r => r.json()),
    ]).then(([m, h, rp]) => {
      setMatches(Array.isArray(m) ? m : [])
      setHeatmaps(h)
      setReport(rp.text || "")
      setLoading(false)
      setRefreshing(false)
    }).catch(() => {
      setLoading(false)
      setRefreshing(false)
    })
  }, [refreshKey])

  const handleRefresh = () => {
    setRefreshing(true)
    setRefreshKey(k => k + 1)
  }

  const wins    = matches.filter(m => m.won).length
  const total   = matches.length
  const avgKda  = total ? (matches.reduce((s, m) => s + m.kda, 0) / total).toFixed(2) : "—"
  const avgHs   = total ? (matches.reduce((s, m) => s + m.headshot_pct, 0) / total).toFixed(1) : "—"
  const avgAcs  = total ? Math.round(matches.reduce((s, m) => s + m.acs, 0) / total) : "—"
  const winrate = total ? Math.round(wins / total * 100) : 0

  const stats = { matches, wins, total, avgKda, avgHs, avgAcs, winrate, heatmaps, report, API }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">RIFT<span>IQ</span></div>
        <div className="header-tag">{PLAYER.name}#{PLAYER.tag}</div>

        {/* Bouton refresh */}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          title="Recharger les données depuis l'API"
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            color: refreshing ? "var(--red)" : "var(--grey)",
            borderRadius: 3,
            padding: "3px 12px",
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            cursor: refreshing ? "not-allowed" : "pointer",
            letterSpacing: 1,
            transition: "all 0.2s",
            animation: refreshing ? "spin 1s linear infinite" : "none",
          }}
        >
          {refreshing ? "⏳" : "↺"} REFRESH
        </button>

        <div className="header-badge">EIP EPITECH · 2025</div>
      </header>

      {/* Sidebar */}
      <nav className="sidebar">
        <div className="nav-section">Navigation</div>
        {NAV.map(n => (
          <div key={n.id}
            className={`nav-item${page === n.id ? " active" : ""}`}
            onClick={() => setPage(n.id)}>
            <span className="nav-icon">{n.icon}</span>
            {n.label}
          </div>
        ))}
        <div className="nav-section" style={{ marginTop: "auto" }}>Données</div>
        <div className="nav-item" style={{ fontSize: "12px", color: "var(--grey)" }}>
          <span className="nav-icon">💾</span>
          {total} matchs
        </div>
      </nav>

      {/* Main */}
      <main className="main">
        {loading ? (
          <div className="loader">
            <div className="loader-ring"/>
            <div className="loader-text">CHARGEMENT DES DONNÉES...</div>
          </div>
        ) : (
          <>
            {page === "overview"  && <Overview      {...stats} />}
            {page === "matches"   && <Matches        {...stats} />}
            {page === "heatmaps"  && <Heatmaps       {...stats} />}
            {page === "report"    && <Report         {...stats} />}
            {page === "coach"     && <Coach          {...stats} />}
            {page === "analysis"  && <MatchAnalysis  {...stats} />}
            {page === "video"     && <VideoCoach               />}
          </>
        )}
      </main>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg) } }
      `}</style>
    </div>
  )
}