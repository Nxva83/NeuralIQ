import { useState, useRef, useEffect } from "react"

const API = "http://localhost:8000"
const NAME = "TuOrdinateur"
const TAG  = "6969"

export default function MatchAnalysis({ matches }) {
  const [selectedMatch, setSelectedMatch] = useState(null)
  const [analysis, setAnalysis] = useState("")
  const [loading, setLoading] = useState(false)
  const [question, setQuestion] = useState("")
  const [chatHistory, setChatHistory] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [analysis, chatHistory])

  const analyzeMatch = async (match) => {
    setSelectedMatch(match)
    setAnalysis("")
    setChatHistory([])
    setLoading(true)

    try {
      const resp = await fetch(
        `${API}/api/match-coach/${NAME}/${TAG}/${encodeURIComponent(match.match_id)}`
      )
      if (!resp.ok) throw new Error(`Erreur ${resp.status}`)

      const reader  = resp.body.getReader()
      const decoder = new TextDecoder()
      let full = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        full += decoder.decode(value)
        setAnalysis(full)
      }
    } catch (e) {
      setAnalysis(`❌ Erreur : ${e.message}`)
    }
    setLoading(false)
  }

  const askQuestion = async () => {
    if (!question.trim() || loading || !selectedMatch) return
    const q = question.trim()
    setQuestion("")
    setLoading(true)
    setChatHistory(prev => [...prev, { role: "user", content: q }])

    try {
      const resp = await fetch(
        `${API}/api/match-coach/${NAME}/${TAG}/${encodeURIComponent(selectedMatch.match_id)}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q })
        }
      )
      const reader  = resp.body.getReader()
      const decoder = new TextDecoder()
      let full = ""
      setChatHistory(prev => [...prev, { role: "assistant", content: "", loading: true }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        full += decoder.decode(value)
        setChatHistory(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: "assistant", content: full, loading: false }
          return updated
        })
      }
    } catch (e) {
      setChatHistory(prev => [...prev, { role: "error", content: e.message }])
    }
    setLoading(false)
  }

  return (
    <div style={{ display: "flex", gap: 16, height: "calc(100vh - 120px)" }}>

      {/* ── Liste des matchs ── */}
      <div style={{
        width: 300, background: "var(--bg2)", border: "1px solid var(--border)",
        borderRadius: 4, display: "flex", flexDirection: "column", overflow: "hidden", flexShrink: 0
      }}>
        <div style={{
          padding: "12px 16px", borderBottom: "1px solid var(--border)",
          fontFamily: "var(--font-head)", fontSize: 13, letterSpacing: 2,
          color: "var(--grey)", textTransform: "uppercase", background: "var(--bg3)"
        }}>
          Sélectionne un match
        </div>
        <div style={{ overflowY: "auto", flex: 1 }}>
          {matches.map((m, i) => {
            const isSelected = selectedMatch?.match_id === m.match_id
            return (
              <div key={i}
                onClick={() => !loading && analyzeMatch(m)}
                style={{
                  padding: "10px 14px",
                  borderLeft: `3px solid ${m.won ? "var(--cyan)" : "var(--red)"}`,
                  borderBottom: "1px solid var(--border)",
                  cursor: loading ? "not-allowed" : "pointer",
                  background: isSelected ? "var(--bg3)" : "transparent",
                  transition: "background 0.15s",
                  opacity: loading && !isSelected ? 0.5 : 1
                }}
                onMouseEnter={e => !isSelected && (e.currentTarget.style.background = "var(--bg3)")}
                onMouseLeave={e => !isSelected && (e.currentTarget.style.background = "transparent")}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{
                    fontFamily: "var(--font-head)", fontSize: 13, fontWeight: 700,
                    color: m.won ? "var(--cyan)" : "var(--red)"
                  }}>
                    {m.won ? "WIN" : "LOSS"}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--grey)" }}>
                    ACS {m.acs}
                  </span>
                </div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: 14, color: "var(--white)", marginBottom: 2 }}>
                  {m.agent}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--grey)" }}>
                    {m.map_name || "—"}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--white)" }}>
                    {m.kills}/{m.deaths}/{m.assists}
                  </span>
                </div>
                {isSelected && (
                  <div style={{
                    marginTop: 6, fontSize: 10, fontFamily: "var(--font-mono)",
                    color: "var(--red)", letterSpacing: 1
                  }}>
                    ▶ ANALYSE EN COURS...
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Zone d'analyse ── */}
      <div style={{
        flex: 1, display: "flex", flexDirection: "column", gap: 12, overflow: "hidden"
      }}>
        {/* Header match sélectionné */}
        {selectedMatch && (
          <div style={{
            background: "var(--bg2)", border: "1px solid var(--border)",
            borderRadius: 4, padding: "12px 16px",
            display: "flex", gap: 20, alignItems: "center"
          }}>
            {[
              { l: "Agent",   v: selectedMatch.agent },
              { l: "Map",     v: selectedMatch.map_name || "—" },
              { l: "K/D/A",   v: `${selectedMatch.kills}/${selectedMatch.deaths}/${selectedMatch.assists}` },
              { l: "HS%",     v: `${selectedMatch.headshot_pct}%` },
              { l: "ACS",     v: selectedMatch.acs },
            ].map((s, i) => (
              <div key={i}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--grey)", letterSpacing: 1 }}>{s.l}</div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: 16, fontWeight: 700, color: "var(--white)" }}>{s.v}</div>
              </div>
            ))}
            <div style={{ marginLeft: "auto" }}>
              <div style={{
                fontFamily: "var(--font-head)", fontSize: 18, fontWeight: 700,
                color: selectedMatch.won ? "var(--cyan)" : "var(--red)"
              }}>
                {selectedMatch.won ? "✅ VICTOIRE" : "❌ DÉFAITE"}
              </div>
            </div>
          </div>
        )}

        {/* Analyse principale */}
        <div style={{
          flex: 1, background: "var(--bg2)", border: "1px solid var(--border)",
          borderRadius: 4, overflow: "hidden", display: "flex", flexDirection: "column"
        }}>
          <div style={{
            padding: "10px 16px", borderBottom: "1px solid var(--border)",
            background: "var(--bg3)", display: "flex", alignItems: "center", gap: 10
          }}>
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: loading ? "var(--gold)" : analysis ? "var(--cyan)" : "var(--grey)",
              boxShadow: loading ? "0 0 8px var(--gold)" : analysis ? "0 0 6px var(--cyan)" : "none",
              animation: loading ? "pulse 1s infinite" : "none"
            }}/>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--grey)" }}>
              {loading ? "Mistral analyse la partie..." : analysis ? "Analyse terminée" : "En attente d'un match"}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
            {!selectedMatch && !analysis && (
              <div style={{ textAlign: "center", marginTop: 80, color: "var(--grey)" }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>🎮</div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: 18, marginBottom: 8, color: "var(--white)" }}>
                  Sélectionne un match à analyser
                </div>
                <div style={{ fontFamily: "var(--font-body)", fontSize: 13, maxWidth: 300, margin: "0 auto" }}>
                  Clique sur n'importe quelle partie dans la liste de gauche pour obtenir une analyse détaillée round par round.
                </div>
              </div>
            )}

            {analysis && (
              <div style={{
                fontFamily: "var(--font-body)", fontSize: 13, lineHeight: 1.75,
                color: "var(--white)", whiteSpace: "pre-wrap"
              }}>
                <div style={{
                  fontFamily: "var(--font-mono)", fontSize: 10,
                  color: "var(--cyan)", marginBottom: 10, letterSpacing: 1
                }}>
                  🤖 RIFTIQ COACH — ANALYSE DÉTAILLÉE
                </div>
                {analysis}
                {loading && <span style={{ color: "var(--cyan)", animation: "blink 1s infinite" }}>▊</span>}
              </div>
            )}

            {/* Chat follow-up */}
            {chatHistory.map((msg, i) => (
              <div key={i} style={{
                marginTop: 16,
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start"
              }}>
                <div style={{
                  maxWidth: "85%", padding: "10px 14px",
                  borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                  background: msg.role === "user" ? "rgba(255,70,85,0.15)" : "var(--bg3)",
                  border: `1px solid ${msg.role === "user" ? "var(--red-dim)" : "var(--border)"}`,
                  fontFamily: "var(--font-body)", fontSize: 13, lineHeight: 1.7,
                  color: "var(--white)", whiteSpace: "pre-wrap"
                }}>
                  {msg.role === "assistant" && (
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--cyan)", marginBottom: 6 }}>
                      🤖 RIFTIQ COACH
                    </div>
                  )}
                  {msg.content}
                  {msg.loading && <span style={{ color: "var(--cyan)", animation: "blink 1s infinite" }}>▊</span>}
                </div>
              </div>
            ))}
            <div ref={bottomRef}/>
          </div>

          {/* Input question follow-up */}
          {analysis && !loading && (
            <div style={{
              padding: "10px 12px", borderTop: "1px solid var(--border)",
              display: "flex", gap: 8, background: "var(--bg2)"
            }}>
              <input
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => e.key === "Enter" && askQuestion()}
                placeholder="Pose une question sur cette partie... (ex: Pourquoi j'ai perdu le round 12 ?)"
                style={{
                  flex: 1, background: "var(--bg3)", border: "1px solid var(--border)",
                  borderRadius: 3, padding: "8px 12px", color: "var(--white)",
                  fontFamily: "var(--font-body)", fontSize: 13, outline: "none"
                }}
              />
              <button onClick={askQuestion} disabled={!question.trim()} style={{
                background: question.trim() ? "var(--red)" : "var(--bg3)",
                border: "1px solid var(--border)", borderRadius: 3,
                padding: "8px 16px", color: "white", fontFamily: "var(--font-head)",
                fontSize: 12, fontWeight: 700, cursor: question.trim() ? "pointer" : "not-allowed",
                letterSpacing: 1, textTransform: "uppercase", transition: "background 0.15s"
              }}>
                Ask
              </button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
      `}</style>
    </div>
  )
}
