import React, { useRef, useState } from "react";

export default function UploadSection({ 
  cvText, 
  setCvText, 
  setFilename, 
  setParsedCv, 
  parsedCv,
  jobText,
  setJobText,
  lastResult,
  setLastResult
}) {
  const [loading, setLoading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
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

  async function computeMatching() {
    setError("");
    const matchingLoading = true;
    
    try {
      const res = await fetch(`${API_BASE}/api/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cvText, jobText }),
      });
      
      if (!res.ok) {
        const errorData = await res.text();
        let errorMsg;
        try {
          const errorJson = JSON.parse(errorData);
          errorMsg = errorJson.error || "Erreur calcul matching";
        } catch {
          errorMsg = `Erreur calcul matching (HTTP ${res.status})`;
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();

      setLastResult({
        score: Math.round((data.score || 0) * 100) / 100,
        similarity_level: data.similarity_level || "Calculé",
        sectional_scores: data.sectional_scores || {},
        skill_analysis: data.skill_analysis || {},
        missing_keywords: data.missing_keywords || [],
        suggestions: data.suggestions || [],
        method: data.method || "Embedding similarity",
        parsed_cv: data.parsed_cv,
        parsed_job: data.parsed_job
      });

    } catch (err) {
      let msg;
      if (err?.message?.includes('Failed to fetch')) {
        msg = "Impossible de se connecter au serveur. Vérifiez qu'il est démarré sur le port 3001.";
      } else {
        msg = err.message || "Impossible de calculer le score. Vérifiez les textes et réessayez.";
      }
      setError(msg);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Titre principal */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">Upload Candidate Profile and Job Description</h1>
        <p className="text-slate-600">Téléchargez un CV et saisissez la description du poste pour analyser la compatibilité</p>
      </div>

      {/* Section Upload côte à côte */}
      <div className="card p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Upload Resume - Gauche */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-700">Upload Resume</h3>
            
            {/* Zone de drag & drop stylisée */}
            <div className="relative">
              <input
                ref={inputRef}
                id="cvfile"
                type="file"
                accept=".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={onFile}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-blue-400 hover:bg-blue-50/50 transition-colors">
                <div className="space-y-3">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-slate-600 font-medium">Drag and drop file here</p>
                    <p className="text-sm text-slate-500">Limit 200MB per file • PDF</p>
                  </div>
                </div>
              </div>
            </div>
            
            <button
              onClick={() => inputRef.current?.click()}
              className="w-full btn btn-outline"
            >
              Browse files
            </button>
            
            {loading && (
              <div className="text-sm text-blue-600 text-center">
                📄 Extraction en cours...
              </div>
            )}
            
            {parsing && (
              <div className="text-sm text-blue-600 text-center">
                ⚙️ Analyse du CV...
              </div>
            )}
          </div>

          {/* Upload Job Description - Droite */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-700">Upload Job Description</h3>
            
            <textarea
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              rows={8}
              placeholder="Collez ici la description du poste..."
              className="w-full p-4 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
            
            <div className="text-sm text-slate-500 text-center">
              Ou glissez-déposez un fichier de description de poste
            </div>
          </div>
        </div>

        {/* Messages d'erreur/warning */}
        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            ❌ {error}
          </div>
        )}

        {warning && !error && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            ⚠️ {warning}
          </div>
        )}

        {/* Bouton de matching */}
        <div className="mt-6 text-center">
          <button
            onClick={computeMatching}
            disabled={!cvText.trim() || !jobText.trim()}
            className="btn btn-primary btn-lg px-8"
          >
            Analyser la compatibilité
          </button>
        </div>
      </div>
    </div>
  );
}