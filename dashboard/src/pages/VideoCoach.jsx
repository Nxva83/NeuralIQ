import { useState, useRef } from "react"

const API = "http://localhost:8000"

export default function VideoCoach() {
  const [file, setFile]           = useState(null)
  const [loading, setLoading]     = useState(false)
  const [progress, setProgress]   = useState("")
  const [result, setResult]       = useState(null)
  const [activeFrame, setActive]  = useState(0)
  const inputRef = useRef(null)

  const handleFile = (e) => {
    const f = e.target.files[0]
    if (f && f.type.startsWith("video/")) {
      setFile(f)
      setResult(null)
      setProgress("")
    }
  }

  const analyze = async () => {
    if (!file || loading) return
    setLoading(true)
    setResult(null)
    setProgress("📸 Envoi de la vidéo...")

    const form = new FormData()
    form.append("video", file)
    form.append("n_frames", "8")

    try {
      const resp = await fetch(`${API}/api/video-coach`, {
        method: "POST",
        body: form,
      })

      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.error || `Erreur ${resp.status}`)
      }

      // Stream de progression
      const reader  = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value)

        // Parse les lignes JSON de progression
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""
        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const data = JSON.parse(line)
            if (data.progress) setProgress(data.progress)
            if (data.result)   setResult(data.result)
          } catch {}
        }
      }
    } catch (e) {
      setProgress(`❌ Erreur : ${e.message}`)
    }
    setLoading(false)
  }

  return (
    <div>
      <div className="section-title">Coach Vidéo — LLaVA Vision IA</div>

      {/* Upload zone */}
      <div className="card" style={{ marginBottom: 16, textAlign: "center" }}>
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => {
            e.preventDefault()
            const f = e.dataTransfer.files[0]
            if (f?.type.startsWith("video/")) { setFile(f); setResult(null) }
          }}
          style={{
            border: `2px dashed ${file ? "var(--cyan)" : "var(--border)"}`,
            borderRadius: 6, padding: "40px 20px", cursor: "pointer",
            transition: "border-color 0.2s",
            background: file ? "rgba(0,255,170,0.05)" : "transparent"
          }}
        >
          <div style={{ fontSize: 48, marginBottom: 12 }}>🎬</div>
          {file ? (
            <>
              <div style={{ fontFamily: "var(--font-head)", fontSize: 16, color: "var(--cyan)" }}>
                {file.name}
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--grey)", marginTop: 4 }}>
                {(file.size / 1024 / 1024).toFixed(1)} MB
              </div>
            </>
          ) : (
            <>
              <div style={{ fontFamily: "var(--font-head)", fontSize: 16, color: "var(--white)", marginBottom: 6 }}>
                Glisse ta vidéo Valorant ici
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--grey)" }}>
                ou clique pour sélectionner un fichier MP4
              </div>
            </>
          )}
        </div>
        <input ref={inputRef} type="file" accept="video/*"
          onChange={handleFile} style={{ display: "none" }} />

        {file && (
          <button onClick={analyze} disabled={loading} style={{
            marginTop: 16, background: loading ? "var(--bg3)" : "var(--red)",
            border: "none", borderRadius: 3, padding: "10px 28px",
            color: "white", fontFamily: "var(--font-head)", fontSize: 15,
            fontWeight: 700, letterSpacing: 1, textTransform: "uppercase",
            cursor: loading ? "not-allowed" : "pointer", transition: "background 0.15s"
          }}>
            {loading ? "⏳ Analyse en cours..." : "🔍 Analyser la vidéo"}
          </button>
        )}
      </div>

      {/* Progression */}
      {progress && !result && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 10, height: 10, borderRadius: "50%",
              background: "var(--gold)", boxShadow: "0 0 8px var(--gold)",
              animation: "pulse 1s infinite", flexShrink: 0
            }}/>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--white)" }}>
              {progress}
            </div>
          </div>
          <div style={{
            marginTop: 12, height: 3, background: "var(--border)",
            borderRadius: 2, overflow: "hidden"
          }}>
            <div style={{
              height: "100%", background: "var(--red)",
              animation: "loading-bar 2s ease infinite",
              width: "40%"
            }}/>
          </div>
        </div>
      )}

      {/* Résultats */}
      {result && (
        <>
          {/* Synthèse */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">🧠 Synthèse — Mistral</div>
            <div style={{
              fontFamily: "var(--font-body)", fontSize: 13,
              lineHeight: 1.75, color: "var(--white)", whiteSpace: "pre-wrap"
            }}>
              {result.synthesis}
            </div>
          </div>

          {/* Frames analysées */}
          <div className="card">
            <div className="card-title">
              📸 Analyse frame par frame ({result.analyses?.length} moments)
            </div>

            {/* Sélecteur de frame */}
            <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
              {result.analyses?.map((a, i) => (
                <button key={i}
                  onClick={() => setActive(i)}
                  style={{
                    background: activeFrame === i ? "var(--red)" : "var(--bg3)",
                    border: `1px solid ${activeFrame === i ? "var(--red)" : "var(--border)"}`,
                    borderRadius: 3, padding: "5px 12px",
                    color: "white", fontFamily: "var(--font-mono)",
                    fontSize: 11, cursor: "pointer", transition: "all 0.15s"
                  }}>
                  {a.timestamp}s
                </button>
              ))}
            </div>

            {/* Détail du frame actif */}
            {result.analyses?.[activeFrame] && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div style={{
                  background: "var(--bg)", border: "1px solid var(--border)",
                  borderRadius: 4, padding: 14
                }}>
                  <div style={{
                    fontFamily: "var(--font-mono)", fontSize: 10,
                    color: "var(--red)", letterSpacing: 1, marginBottom: 8
                  }}>
                    🎯 POSITIONNEMENT — {result.analyses[activeFrame].timestamp}s
                  </div>
                  <div style={{
                    fontFamily: "var(--font-body)", fontSize: 13,
                    lineHeight: 1.7, color: "var(--white)"
                  }}>
                    {result.analyses[activeFrame].positioning || "Analyse indisponible"}
                  </div>
                </div>

                <div style={{
                  background: "var(--bg)", border: "1px solid var(--border)",
                  borderRadius: 4, padding: 14
                }}>
                  <div style={{
                    fontFamily: "var(--font-mono)", fontSize: 10,
                    color: "var(--cyan)", letterSpacing: 1, marginBottom: 8
                  }}>
                    🗺️ MINIMAP — {result.analyses[activeFrame].timestamp}s
                  </div>
                  <div style={{
                    fontFamily: "var(--font-body)", fontSize: 13,
                    lineHeight: 1.7, color: "var(--white)"
                  }}>
                    {result.analyses[activeFrame].minimap || "Minimap non détectée"}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes loading-bar {
          0%   { transform: translateX(-100%) }
          50%  { transform: translateX(150%) }
          100% { transform: translateX(400%) }
        }
      `}</style>
    </div>
  )
}
