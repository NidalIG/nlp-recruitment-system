import React, { useRef, useState } from "react";
import userApiService from "../../services/userApiService";

export default function UploadSection({
  cvText,
  setCvText,
  setFilename,
  setParsedCv,
  parsedCv,
  jobText,
  setJobText,
  lastResult,
  setLastResult,
  onDataChanged,
}) {
  const [loading, setLoading] = useState(false);     // extraction
  const [parsing, setParsing] = useState(false);     // parsing CV
  const [matching, setMatching] = useState(false);   // spinner matching
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const [localFilename, setLocalFilename] = useState("");
  const inputRef = useRef(null);
  const jobRef = useRef(null);

  const API_BASE =
    import.meta.env.VITE_API_BASE ||
    (window.location.hostname === "localhost" ? "http://localhost:3001" : "");

  const getAuthHeaders = () => {
    const token = sessionStorage.getItem("authToken");
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  // ---- helpers ----
  function buildTextFromParsedCv(cv = {}) {
    // Transforme un CV structuré en texte "lisible" pour l’endpoint /api/match
    const lines = [];
    const name = cv.name || cv.full_name || "Candidat";
    const headline =
      cv.headline ||
      cv.title ||
      (cv.experience?.[0]?.job_title || cv.experience?.[0]?.title) ||
      "Profil";
    lines.push(`${name} — ${headline}`);

    if (Array.isArray(cv.skills) && cv.skills.length) {
      lines.push(`Compétences: ${cv.skills.join(", ")}`);
    }
    if (Array.isArray(cv.certifications) && cv.certifications.length) {
      const certs = cv.certifications
        .map((c) => (typeof c === "string" ? c : c?.name || c?.title))
        .filter(Boolean);
      if (certs.length) lines.push(`Certifications: ${certs.join(", ")}`);
    }
    if (Array.isArray(cv.languages) && cv.languages.length) {
      const langs = cv.languages.map((l) => (typeof l === "string" ? l : l?.name)).filter(Boolean);
      if (langs.length) lines.push(`Langues: ${langs.join(", ")}`);
    }

    if (Array.isArray(cv.experience) && cv.experience.length) {
      lines.push("Expériences:");
      cv.experience.slice(0, 6).forEach((e) => {
        const role = e.job_title || e.title || "Poste";
        const company = e.company || e.company_name || e.employer || "Entreprise";
        const desc =
          e.description ||
          (Array.isArray(e.responsibilities) ? e.responsibilities.slice(0, 5).join("; ") : "");
        lines.push(`- ${role} @ ${company}${desc ? ` — ${desc}` : ""}`);
      });
    }

    if (Array.isArray(cv.education) && cv.education.length) {
      lines.push("Formation:");
      cv.education.slice(0, 5).forEach((ed) => {
        const deg = ed.degree || ed.diploma || ed.title || "Diplôme";
        const inst = ed.school || ed.institution || "";
        lines.push(`- ${deg}${inst ? ` — ${inst}` : ""}`);
      });
    }
    return lines.join("\n");
  }

  async function fetchLatestCvTextFromDB() {
    // Récupère le dernier CV PARSÉ et le recompose en texte
    const res = await fetch(`${API_BASE}/api/results?type=cv&limit=1`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const t = await res.text();
      try {
        const j = JSON.parse(t);
        throw new Error(j?.error || `HTTP ${res.status}`);
      } catch {
        throw new Error(`HTTP ${res.status}`);
      }
    }
    const list = await res.json();
    const item = Array.isArray(list) ? list[0] : null;
    const cvData = item?.data;
    if (!cvData) return null;
    const parsed = typeof cvData === "object" && cvData.parsed_cv ? cvData.parsed_cv : cvData;
    const text = buildTextFromParsedCv(parsed || {});
    return {
      text,
      filename: item?.meta?.original_filename || "Dernier CV (base)",
      parsed,
    };
  }

  // ---- upload fichier ----
  async function onFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    const okTypes = [
      "application/pdf",
      "text/plain",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];
    const isOk = okTypes.includes(file.type) || /\.(pdf|txt|docx)$/i.test(file.name);
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
        try {
          const errorJson = JSON.parse(errorData);
          throw new Error(errorJson.error || `Upload échoué (HTTP ${res.status})`);
        } catch {
          throw new Error(`Upload échoué (HTTP ${res.status})`);
        }
      }

      const data = await res.json();

      setCvText(data.text || "");
      setFilename?.(data.filename || file.name);
      setLocalFilename(data.filename || file.name);

      if (data.warning) setWarning(data.warning);

      if (data.text && data.text.length > 100) {
        await parseCV(data.text);
      }
    } catch (err) {
      const msg =
        err?.name === "AbortError"
          ? "Délai dépassé. Vérifiez que le serveur est démarré."
          : err?.message?.includes("Failed to fetch")
          ? "Impossible de se connecter au serveur. Vérifiez qu'il est démarré sur le port 3001."
          : err?.message || "Échec d'upload.";
      setError(msg);
      inputRef.current && (inputRef.current.value = "");
      setLocalFilename("");
    } finally {
      setLoading(false);
    }
  }

  // ---- parse CV (texte -> JSON structuré) ----
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
        headers: getAuthHeaders(),
        body: JSON.stringify({ cvText: textToparse }),
      });

      if (!res.ok) {
        const t = await res.text();
        try {
          const j = JSON.parse(t);
          throw new Error(j?.error || "Erreur de parsing");
        } catch {
          throw new Error(`Erreur de parsing (HTTP ${res.status})`);
        }
      }

      const data = await res.json();
      setParsedCv?.(data.parsed_cv);
      onDataChanged?.(); // notifie ChatSection pour rafraîchir les cartes
    } catch (err) {
      const msg = err?.message?.includes("Failed to fetch")
        ? "Impossible de se connecter au serveur pour le parsing."
        : err.message || "Erreur lors du parsing structuré";
      setError(msg);
    } finally {
      setParsing(false);
    }
  }

  // ---- parse JD (optionnel bouton) ----
  async function handleParseJob() {
    if (!jobText?.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await userApiService.parseJob(jobText.trim());
      // Option: set parsed job in parent state
      onDataChanged?.();
    } catch (err) {
      setError(err.message || "Erreur parsing job");
    } finally {
      setLoading(false);
    }
  }

  // ---- matching ----
  async function computeMatching() {
    setError("");
    setWarning("");

    // Vérif JD
    if (!jobText?.trim()) {
      setError("Veuillez remplir la section Job Description avant d’analyser.");
      jobRef.current?.focus();
      return;
    }

    // Prépare le texte CV : si vide → aller le chercher en base
    let cvTextToUse = (cvText || "").trim();
    if (!cvTextToUse) {
      try {
        const latest = await fetchLatestCvTextFromDB();
        if (!latest || !latest.text?.trim()) {
          setError(
            "Aucun CV téléversé et aucun CV trouvé en base. Veuillez téléverser un CV avant d’analyser."
          );
          inputRef.current?.focus();
          return;
        }
        cvTextToUse = latest.text;
        // met à jour l’UI pour transparence
        setCvText(latest.text);
        setParsedCv?.(latest.parsed || {});
        setFilename?.(latest.filename);
        setLocalFilename(latest.filename);
        setWarning("Aucun CV téléversé. Utilisation du dernier CV enregistré.");
        onDataChanged?.();
      } catch (e) {
        setError(
          e?.message
            ? `Impossible de récupérer le dernier CV en base: ${e.message}`
            : "Impossible de récupérer le dernier CV en base."
        );
        return;
      }
    }

    setMatching(true);
    try {
      const res = await fetch(`${API_BASE}/api/match`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ cvText: cvTextToUse, jobText: jobText }),
      });

      if (!res.ok) {
        const t = await res.text();
        try {
          const j = JSON.parse(t);
          throw new Error(j?.error || "Erreur calcul matching");
        } catch {
          throw new Error(`Erreur calcul matching (HTTP ${res.status})`);
        }
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
        parsed_job: data.parsed_job,
      });

      // Pousser les messages de recommandations dans le chat si dispo
      if (Array.isArray(data.messages) && data.messages.length && window.__chatAppend) {
        data.messages.forEach((m) => window.__chatAppend(m));
      }

      // Message final dans le chat
      if (window.__chatAppend) {
        window.__chatAppend({
          type: "system",
          text: `✅ Analyse terminée — Score: ${Math.round((data.score || 0) * 100) / 100} / 100.`,
        });
      }
    } catch (err) {
      const msg = err?.message?.includes("Failed to fetch")
        ? "Impossible de se connecter au serveur. Vérifiez qu'il est démarré sur le port 3001."
        : err.message || "Impossible de calculer le score. Vérifiez les textes et réessayez.";
      setError(msg);
    } finally {
      setMatching(false);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Titre principal */}
      <div className="text-center">
        <h1 className="mb-2 text-2xl font-bold text-slate-800">
          Upload Candidate Profile and Job Description
        </h1>
        <p className="text-slate-600">
          Téléchargez un CV et saisissez la description du poste pour analyser la compatibilité
        </p>
      </div>

      {/* Section Upload */}
      <div className="card p-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Upload Resume */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-700">Upload Resume</h3>

            <div className="relative">
              <input
                ref={inputRef}
                id="cvfile"
                type="file"
                accept=".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={onFile}
                className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
              />
              <div className="rounded-lg border-2 border-dashed border-slate-300 p-8 text-center transition-colors hover:border-blue-400 hover:bg-blue-50/50">
                <div className="space-y-3">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
                    <svg className="h-8 w-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-slate-600">Drag and drop file here</p>
                    <p className="text-sm text-slate-500">Limit 200MB per file • PDF/TXT/DOCX</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Fichier choisi */}
            {localFilename && (
              <div className="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                <span className="truncate">📄 {localFilename}</span>
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="text-blue-600 hover:underline"
                >
                  Changer
                </button>
              </div>
            )}

            <button type="button" onClick={() => inputRef.current?.click()} className="btn btn-outline w-full">
              Browse files
            </button>

            {loading && <div className="text-center text-sm text-blue-600">📄 Extraction en cours...</div>}
            {parsing && <div className="text-center text-sm text-blue-600">⚙️ Analyse du CV...</div>}
          </div>

          {/* Job Description */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-700">Upload Job Description</h3>

            <textarea
              ref={jobRef}
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              rows={8}
              placeholder="Collez ici la description du poste..."
              className="w-full resize-none rounded-lg border border-slate-300 p-4 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
            />

            <button
              onClick={handleParseJob}
              disabled={!jobText?.trim() || loading}
              className="w-full btn btn-outline"
            >
              Analyser l’offre
            </button>

            <div className="text-center text-sm text-slate-500">
              Ou glissez-déposez un fichier de description de poste
            </div>
          </div>
        </div>

        {/* Erreurs / warnings */}
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

        {/* Action */}
        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={computeMatching}
            disabled={loading || parsing || matching || !jobText.trim()}
            className="btn btn-primary btn-lg px-8 disabled:opacity-60"
          >
            {matching ? "Analyse en cours..." : "Analyser la compatibilité"}
          </button>
        </div>
      </div>
    </div>
  );
}
