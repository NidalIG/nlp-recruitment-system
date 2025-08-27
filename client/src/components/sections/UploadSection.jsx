import React, { useRef, useState } from "react";

export default function UploadSection({ 
  cvText, 
  setCvText, 
  setFilename, 
  setParsedCv, 
  parsedCv 
}) {
  const [loading, setLoading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const [showParsed, setShowParsed] = useState(false);
  const inputRef = useRef(null);

  const API_BASE =
    import.meta.env.VITE_API_BASE ||
    (window.location.hostname === "localhost" ? "http://localhost:3001" : "");

  async function onFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    const okTypes = ["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
    const isOk =
      okTypes.includes(file.type) ||
      /\.(pdf|txt|docx)$/i.test(file.name);
    
    if (!isOk) {
      setError("Type non supporté. Choisissez un PDF, TXT ou DOCX.");
      e.target.value = "";
      return;
    }

    setError("");
    setWarning("");
    setLoading(true);

    try {
      const form = new FormData();
      form.append("file", file);

      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 30000);

      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      
      clearTimeout(timer);

      if (!res.ok) {
        const errorData = await res.text();
        let errorMsg;
        try {
          const errorJson = JSON.parse(errorData);
          errorMsg = errorJson.error || `Upload échoué (HTTP ${res.status})`;
        } catch {
          errorMsg = `Upload échoué (HTTP ${res.status})`;
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();

      setCvText(data.text || "");
      setFilename?.(data.filename || file.name);

      if (data.warning) {
        setWarning(data.warning);
      }

      // Auto-parse si le texte est suffisant
      if (data.text && data.text.length > 100) {
        await parseCV(data.text);
      }

    } catch (err) {
      let msg;
      if (err?.name === "AbortError") {
        msg = "Délai dépassé. Vérifiez que le serveur est démarré.";
      } else if (err?.message?.includes('Failed to fetch')) {
        msg = "Impossible de se connecter au serveur. Vérifiez qu'il est démarré sur le port 3001.";
      } else {
        msg = err?.message || "Échec d'upload.";
      }
      setError(msg);
      if (inputRef.current) inputRef.current.value = "";
    } finally {
      setLoading(false);
    }
  }

  async function parseCV(textToparse = cvText) {
    if (!textToparse.trim()) {
      setError("Aucun texte à parser");
      return;
    }

    setParsing(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/parse-cv`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cvText: textToparse }),
      });

      if (!res.ok) {
        const errorData = await res.text();
        let errorMsg;
        try {
          const errorJson = JSON.parse(errorData);
          errorMsg = errorJson.error || "Erreur de parsing";
        } catch {
          errorMsg = `Erreur de parsing (HTTP ${res.status})`;
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();
      setParsedCv?.(data.parsed_cv);
      setShowParsed(true);

    } catch (err) {
      let msg;
      if (err?.message?.includes('Failed to fetch')) {
        msg = "Impossible de se connecter au serveur pour le parsing.";
      } else {
        msg = err.message || "Erreur lors du parsing structuré";
      }
      setError(msg);
    } finally {
      setParsing(false);
    }
  }

  return (
    <div id="upload" className="space-y-4 animate-fade-in">
      <h2 className="text-base font-semibold text-slate-800">Upload & Parsing</h2>

      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          id="cvfile"
          type="file"
          accept=".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={onFile}
          className="input file:mr-3 file:rounded-md file:border-0 file:bg-slate-900 file:px-3 file:py-2 file:text-white hover:file:bg-slate-800"
        />
        {loading && <span className="text-sm text-slate-500">Extraction…</span>}
        {parsing && <span className="text-sm text-blue-500">Parsing structuré…</span>}
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          ❌ {error}
        </div>
      )}

      {warning && !error && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          ⚠️ {warning}
        </div>
      )}

        <div className="mb-3 flex items-center justify-between">
          {/* <label className="text-sm font-medium text-slate-600">
            Texte extrait du CV
          </label> */}
          {cvText && (
            <button
              onClick={() => parseCV()}
              disabled={parsing}
              className="btn btn-sm btn-secondary"
            >
              {/* {parsing ? "Parsing..." : "📋 Parser structure"} */}
            </button>
          )}
        </div>
        
        {/* <textarea
          value={cvText}
          onChange={(e) => setCvText(e.target.value)}
          rows={8}
          placeholder="Le texte du CV sera affiché ici après l'upload..."
          className="input"
        /> */}
     

      {/* Résultat du parsing structuré 
      
      {parsedCv && (
        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <label className="text-sm font-medium text-slate-600">
               Données structurées extraites
            </label>
            <button
              onClick={() => setShowParsed(!showParsed)}
              className="btn btn-sm"
            >
              {showParsed ? "Masquer" : "Afficher"}
            </button>
          </div>
          
          {showParsed && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <strong>👤 Nom:</strong> {parsedCv.name || "N/A"}
                </div>
                <div>
                  <strong>📧 Email:</strong> {parsedCv.email || "N/A"}
                </div>
                <div>
                  <strong>📞 Téléphone:</strong> {parsedCv.phone || "N/A"}
                </div>
              </div>
              
              {parsedCv.skills?.length > 0 && (
                <div>
                  <strong>🛠️ Compétences:</strong>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {parsedCv.skills.map((skill, idx) => (
                      <span key={idx} className="badge bg-blue-100 text-blue-800">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {parsedCv.experience?.length > 0 && (
                <div>
                  <strong>💼 Expérience:</strong>
                  <div className="mt-2 space-y-2">
                    {parsedCv.experience.slice(0, 2).map((exp, idx) => (
                      <div key={idx} className="text-sm bg-slate-50 p-2 rounded">
                        <strong>{exp.job_title}</strong> chez {exp.company_name} ({exp.years_worked})
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {parsedCv.education?.length > 0 && (
                <div>
                  <strong>🎓 Formation:</strong>
                  <div className="mt-2 space-y-1">
                    {parsedCv.education.map((edu, idx) => (
                      <div key={idx} className="text-sm">
                        {edu.degree} - {edu.institution_name} ({edu.graduation_year})
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )} */}
    </div>
  );
}