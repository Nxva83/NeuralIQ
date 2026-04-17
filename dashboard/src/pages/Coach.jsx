import { useState, useRef, useEffect } from "react"

const API = "http://localhost:8000"

const QUICK_QUESTIONS = [
  "Quel est mon plus gros point faible en ce moment ?",
  "Sur quelle map dois-je m'améliorer en priorité ?",
  "Quel agent devrais-je arrêter de jouer ?",
  "Comment améliorer mon headshot % ?",
  "Explique-moi mes zones de mort les plus dangereuses",
  "Donne-moi un plan d'entraînement pour cette semaine",
]

export default function Coach({ matches, heatmaps }) {
  const [messages, setMessages]   = useState([])
  const [input, setInput]         = useState("")
  const [loading, setLoading]     = useState(false)
  const [hasReport, setHasReport] = useState(false)
  const bottomRef = useRef(null)

  const name = "TuOrdinateur"
  const tag  = "6969"

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const streamResponse = async (url, options = {}) => {
    const resp = await fetch(url, options)
    if (!resp.ok) throw new Error(`Erreur ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let full = ""

    // Ajoute un message assistant vide
    setMessages(prev => [...prev, { role: "assistant", content: "", loading: true }])

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      full += chunk
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: "assistant", content: full, loading: false }
        return updated
      })
    }
    return full
  }

  const generateReport = async () => {
    setLoading(true)
    setMessages([{ role: "system", content: "🧠 Analyse de tes parties en cours..." }])
    try {
      await streamResponse(`${API}/api/coach/${name}/${tag}`)
      setHasReport(true)
    } catch (e) {
      setMessages(prev => [...prev, { role: "error", content: `Erreur : ${e.message}` }])
    }
    setLoading(false)
  }

  const sendMessage = async (text) => {
    const question = text || input.trim()
    if (!question || loading) return
    setInput("")
    setLoading(true)

    setMessages(prev => [...prev, { role: "user", content: question }])

    try {
      await streamResponse(`${API}/api/coach/${name}/${tag}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      })
    } catch (e) {
      setMessages(prev => [...prev, { role: "error", content: `Erreur : ${e.message}` }])
    }
    setLoading(false)
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 120px)", gap: 16 }}>
      <div className="section-title">Coach IA — Mistral 7B</div>

      {/* Stats rapides */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {[
          { l: "Matchs", v: matches.length },
          { l: "Winrate", v: `${matches.length ? Math.round(matches.filter(m=>m.won).length/matches.length*100) : 0}%` },
          { l: "KDA moy.", v: matches.length ? (matches.reduce((s,m)=>s+m.kda,0)/matches.length).toFixed(2) : "—" },
          { l: "Maps analysées", v: Object.keys(heatmaps).length },
        ].map((s, i) => (
          <div key={i} style={{
            background: "var(--bg2)", border: "1px solid var(--border)",
            borderRadius: 4, padding: "8px 16px", fontFamily: "var(--font-mono)",
            fontSize: 12
          }}>
            <span style={{ color: "var(--grey)" }}>{s.l} </span>
            <span style={{ color: "var(--cyan)", fontWeight: 700 }}>{s.v}</span>
          </div>
        ))}
      </div>

      {/* Zone de chat */}
      <div style={{
        flex: 1, background: "var(--bg2)", border: "1px solid var(--border)",
        borderRadius: 4, display: "flex", flexDirection: "column", overflow: "hidden",
        position: "relative"
      }}>
        {/* Top bar */}
        <div style={{
          padding: "10px 16px", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", gap: 10,
          background: "var(--bg3)"
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: loading ? "var(--gold)" : "var(--cyan)",
            boxShadow: `0 0 6px ${loading ? "var(--gold)" : "var(--cyan)"}`,
            animation: loading ? "pulse 1s infinite" : "none"
          }}/>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--grey)" }}>
            {loading ? "Mistral réfléchit..." : "Mistral 7B — prêt"}
          </span>
          {!hasReport && !loading && (
            <button onClick={generateReport} style={{
              marginLeft: "auto", background: "var(--red)", color: "white",
              border: "none", borderRadius: 3, padding: "5px 14px",
              fontFamily: "var(--font-head)", fontSize: 13, fontWeight: 700,
              letterSpacing: 1, cursor: "pointer", textTransform: "uppercase"
            }}>
              Générer le rapport
            </button>
          )}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", marginTop: 60 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🧠</div>
              <div style={{ fontFamily: "var(--font-head)", fontSize: 18, color: "var(--white)", marginBottom: 8 }}>
                Ton coach IA personnel
              </div>
              <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--grey)", maxWidth: 400, margin: "0 auto" }}>
                Clique sur <strong style={{ color: "var(--red)" }}>Générer le rapport</strong> pour une analyse complète,
                ou pose directement une question ci-dessous.
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={{
              display: "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start"
            }}>
              <div style={{
                maxWidth: "85%",
                padding: "10px 14px",
                borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                background: msg.role === "user"
                  ? "rgba(255,70,85,0.15)"
                  : msg.role === "error"
                  ? "rgba(255,70,85,0.1)"
                  : msg.role === "system"
                  ? "rgba(0,200,136,0.08)"
                  : "var(--bg3)",
                border: `1px solid ${msg.role === "user" ? "var(--red-dim)" : "var(--border)"}`,
                fontFamily: "var(--font-body)",
                fontSize: 13,
                lineHeight: 1.7,
                color: msg.role === "error" ? "var(--red)" : msg.role === "system" ? "var(--cyan)" : "var(--white)",
                whiteSpace: "pre-wrap",
              }}>
                {msg.role === "assistant" && (
                  <div style={{
                    fontFamily: "var(--font-mono)", fontSize: 10,
                    color: "var(--cyan)", marginBottom: 6, letterSpacing: 1
                  }}>
                    🤖 RIFTIQ COACH
                  </div>
                )}
                {msg.content}
                {msg.loading && <span style={{ animation: "blink 1s infinite", color: "var(--cyan)" }}>▊</span>}
              </div>
            </div>
          ))}
          <div ref={bottomRef}/>
        </div>

        {/* Questions rapides */}
        {hasReport && (
          <div style={{
            padding: "8px 12px", borderTop: "1px solid var(--border)",
            display: "flex", gap: 6, flexWrap: "wrap", background: "var(--bg3)"
          }}>
            {QUICK_QUESTIONS.map((q, i) => (
              <button key={i} onClick={() => sendMessage(q)} disabled={loading} style={{
                background: "var(--bg2)", border: "1px solid var(--border)",
                color: "var(--grey)", borderRadius: 3, padding: "4px 10px",
                fontFamily: "var(--font-mono)", fontSize: 10, cursor: "pointer",
                transition: "all 0.15s", letterSpacing: 0.5,
                opacity: loading ? 0.5 : 1
              }}
              onMouseEnter={e => { e.target.style.borderColor = "var(--red)"; e.target.style.color = "var(--white)" }}
              onMouseLeave={e => { e.target.style.borderColor = "var(--border)"; e.target.style.color = "var(--grey)" }}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{
          padding: "10px 12px", borderTop: "1px solid var(--border)",
          display: "flex", gap: 8, background: "var(--bg2)"
        }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Pose une question à ton coach... (Entrée pour envoyer)"
            disabled={loading}
            style={{
              flex: 1, background: "var(--bg3)", border: "1px solid var(--border)",
              borderRadius: 3, padding: "8px 12px", color: "var(--white)",
              fontFamily: "var(--font-body)", fontSize: 13, outline: "none",
              opacity: loading ? 0.6 : 1
            }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            style={{
              background: loading || !input.trim() ? "var(--bg3)" : "var(--red)",
              border: "1px solid var(--border)", borderRadius: 3,
              padding: "8px 18px", color: "white", fontFamily: "var(--font-head)",
              fontSize: 13, fontWeight: 700, cursor: loading || !input.trim() ? "not-allowed" : "pointer",
              letterSpacing: 1, textTransform: "uppercase", transition: "background 0.15s"
            }}
          >
            Envoyer
          </button>
        </div>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
      `}</style>
    </div>
  )
}
