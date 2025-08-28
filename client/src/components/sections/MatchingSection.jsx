import React, { useState } from "react";
import ProgressCircle from "../ui/ProgressCircle.jsx";

export default function MatchingSection({ 
  cvText, 
  jobText, 
  setJobText, 
  lastResult, 
  setLastResult,
  parsedCv 
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [parsedJob, setParsedJob] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [detailedReport, setDetailedReport] = useState("");

  const API_BASE =
    import.meta.env.VITE_API_BASE ||
    (window.location.hostname === "localhost" ? "http://localhost:3001" : "");

  async function parseJob() {
    if (!jobText.trim()) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/parse-job`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobText }),
      });
      
      if (!res.ok) {
        const errorData = await res.text();
        let errorMsg;
        try {
          const errorJson = JSON.parse(errorData);
          errorMsg = errorJson.error || "Erreur parsing job";
        } catch {
          errorMsg = `Erreur parsing job (HTTP ${res.status})`;
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();
      if (data.parsed_job) {
        setParsedJob(data.parsed_job);
      }
    } catch (err) {
      console.log("Erreur parsing job:", err.message);
      setError(`Parsing job échoué: ${err.message}`);
    }
  }

  async function computeMatching() {
    setError("");
    setLoading(true);
    
    try {
      // Parse job d'abord si pas encore fait
      if (!parsedJob) {
        await parseJob();
      }

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

      // Mettre à jour parsedJob si reçu
      if (data.parsed_job) {
        setParsedJob(data.parsed_job);
      }

    } catch (err) {
      let msg;
      if (err?.message?.includes('Failed to fetch')) {
        msg = "Impossible de se connecter au serveur. Vérifiez qu'il est démarré sur le port 3001.";
      } else {
        msg = err.message || "Impossible de calculer le score. Vérifiez les textes et réessayez.";
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function generateDetailedReport() {
    try {
      const res = await fetch(`${API_BASE}/api/detailed-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cvText, jobText }),
      });
      
      if (!res.ok) {
        const errorData = await res.text();
        let errorMsg;
        try {
          const errorJson = JSON.parse(errorData);
          errorMsg = errorJson.error || "Erreur génération rapport";
        } catch {
          errorMsg = `Erreur génération rapport (HTTP ${res.status})`;
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();
      
      if (data.report) {
        setDetailedReport(data.report);
        setShowReport(true);
      }
    } catch (err) {
      let msg;
      if (err?.message?.includes('Failed to fetch')) {
        msg = "Impossible de se connecter au serveur pour le rapport.";
      } else {
        msg = err.message || "Erreur génération du rapport détaillé";
      }
      setError(msg);
    }
  }

  const getScoreColor = (score) => {
    if (score >= 85) return "text-green-600";
    if (score >= 70) return "text-blue-600";
    if (score >= 55) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreBackground = (score) => {
    if (score >= 85) return "bg-green-50 border-green-200";
    if (score >= 70) return "bg-blue-50 border-blue-200";
    if (score >= 55) return "bg-yellow-50 border-yellow-200";
    return "bg-red-50 border-red-200";
  };

  return (
    <div id="matching" className="space-y-4 animate-fade-in">
      
      {/* Section Job Description */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-800">Job Description</h2>
            {jobText && (
              <button
                onClick={parseJob}
                className="btn btn-sm btn-secondary"
              >
                
              </button>
            )}
          </div>
          
          <textarea
            value={jobText}
            onChange={(e) => setJobText(e.target.value)}
            rows={8}
            placeholder="Collez ici l'offre d'emploi..."
            className="input"
          />
          
          <div className="flex gap-2">
            <button
              onClick={computeMatching}
              disabled={loading || !cvText.trim() || !jobText.trim()}
              className="btn btn-primary flex-1"
            >
              {loading ? "Calcul..." : " Calculer le matching"}
            </button>
            
            {/* {lastResult && (
              <button
                onClick={generateDetailedReport}
                className="btn btn-secondary"
              >
                Rapport
              </button>
            )} */}
          </div>

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              ❌ {error}
            </div>
          )}
        </div>

        {/* Section Résultats */}
        <div className={`card p-4 space-y-4 ${lastResult?.score ? getScoreBackground(lastResult.score) : ''}`}>
          <div className="flex items-center gap-4">
            <ProgressCircle value={lastResult?.score ?? 0} />
            <div className="text-sm text-slate-600">
              {lastResult?.score != null ? (
                <>
                  <div className={`text-lg font-bold ${getScoreColor(lastResult.score)}`}>
                    {lastResult.score}% - {lastResult.similarity_level}
                  </div>
                  <div className="text-slate-500 text-xs">
                    {lastResult.method || "Méthode: similarité embedding"}
                  </div>
                </>
              ) : (
                <div className="text-slate-500">Calculez pour voir le score...</div>
              )}
            </div>
          </div>

          {/* Scores sectionnels */}
          {lastResult?.sectional_scores && (
            <div>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="mb-2 text-sm font-medium text-slate-600 hover:text-slate-800"
              >
                 Scores détaillés {showDetails ? "▼" : "▶"}
              </button>
              
              {showDetails && (
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>Global: <strong>{lastResult.sectional_scores.global || 0}%</strong></div>
                  <div>Compétences: <strong>{lastResult.sectional_scores.skills || 0}%</strong></div>
                  <div>Expérience: <strong>{lastResult.sectional_scores.experience || 0}%</strong></div>
                  <div>Formation: <strong>{lastResult.sectional_scores.education || 0}%</strong></div>
                </div>
              )}
            </div>
          )}

          {/* Analyse des compétences */}
          {lastResult?.skill_analysis && (
            <div>
              <div className="mb-2 text-sm font-medium text-slate-600">
                Analyse des compétences
              </div>
              <div className="text-sm space-y-1">
                <div>Similarité moyenne: <strong>{lastResult.skill_analysis.average_skill_similarity || 0}%</strong></div>
                <div>Couverture: <strong>{lastResult.skill_analysis.skill_coverage || 0}%</strong></div>
              </div>
              
              {lastResult.skill_analysis.top_skill_matches?.length > 0 && showDetails && (
                <div className="mt-2">
                  <div className="text-xs text-slate-500 mb-1">Top correspondances:</div>
                  {lastResult.skill_analysis.top_skill_matches.slice(0, 3).map((match, i) => (
                    <div key={i} className="text-xs bg-white p-1 rounded mb-1">
                      <strong>{match.job_skill}</strong> → {match.matched_cv_skill} 
                      <span className="text-green-600"> ({Math.round((match.similarity || 0) * 100)}%)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mots-clés manquants */}
          {lastResult?.missing_keywords?.length > 0 && (
            <div>
              <div className="mb-2 text-sm font-medium text-slate-600">
                 Compétences à développer
              </div>
              <div className="flex flex-wrap gap-2">
                {lastResult.missing_keywords.slice(0, 8).map((keyword, i) => (
                  <span
                    key={i}
                    className="badge border-amber-200 bg-amber-50 text-amber-700"
                  >
                    {keyword}
                  </span>
                ))}
                {lastResult.missing_keywords.length > 8 && (
                  <span className="text-xs text-slate-500">
                    +{lastResult.missing_keywords.length - 8} autres...
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Suggestions */}
          {lastResult?.suggestions?.length > 0 && (
            <div>
              <div className="mb-2 text-sm font-medium text-slate-600">
                Suggestions d'amélioration
              </div>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                {lastResult.suggestions.map((suggestion, i) => (
                  <li key={i}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Job parsé */}
      {/* {parsedJob && (
        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-600">
              🎯 Job Description analysée
            </h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <strong>📋 Titre:</strong> {parsedJob.title || "N/A"}
            </div>
            <div>
              <strong>🏢 Entreprise:</strong> {parsedJob.company || "N/A"}
            </div>
            <div>
              <strong>📍 Lieu:</strong> {parsedJob.location || "N/A"}
            </div>
            <div>
              <strong>📄 Contrat:</strong> {parsedJob.contract || "N/A"}
            </div>
            <div>
              <strong>⏰ Expérience:</strong> {parsedJob.experience_required || "N/A"}
            </div>
            <div>
              <strong>🎓 Formation:</strong> {parsedJob.education_required || "N/A"}
            </div>
          </div>
          
          {parsedJob.required_skills?.length > 0 && (
            <div className="mt-3">
              <strong>🛠️ Compétences requises:</strong>
              <div className="flex flex-wrap gap-2 mt-2">
                {parsedJob.required_skills.map((skill, idx) => (
                  <span key={idx} className="badge bg-green-100 text-green-800">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )} */}

      {/* Rapport détaillé modal */}
      {showReport && detailedReport && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Rapport détaillé de matching</h3>
              <button
                onClick={() => setShowReport(false)}
                className="btn btn-sm"
              >
                ❌ Fermer
              </button>
            </div>
            
            <pre className="whitespace-pre-wrap text-sm bg-slate-50 p-4 rounded border">
              {detailedReport}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}