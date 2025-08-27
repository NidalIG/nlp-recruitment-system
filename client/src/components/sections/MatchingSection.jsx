import React, { useState } from "react";
import ProgressCircle from "../ui/ProgressCircle.jsx";

export default function MatchingSection({ cvText, jobText, setJobText, lastResult, setLastResult }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function compute() {
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cvText, jobText }),
      });
      const ct = res.headers.get("content-type") || "";
      const data = ct.includes("application/json") ? await res.json() : {};
      if (!res.ok) throw new Error(data?.error || "Erreur calcul matching");
      setLastResult({
        score: Math.round(data.score * 100) / 100,
        missingKeywords: data.missingKeywords || [],
        suggestions: data.suggestions || [],
      });
    } catch (err) {
      setError("Impossible de calculer le score. Vérifiez les textes et réessayez.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div id="matching" className="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-fade-in">
      <div className="space-y-3">
        <h2 className="text-base font-semibold text-slate-800">Job Description & Scoring</h2>
        <textarea
          value={jobText}
          onChange={(e) => setJobText(e.target.value)}
          rows={10}
          placeholder="Collez ici l'offre d'emploi..."
          className="input"
        />
        <button
          onClick={compute}
          disabled={loading || !cvText.trim() || !jobText.trim()}
          className="btn btn-primary"
        >
          {loading ? "Calcul..." : "Calculer le score"}
        </button>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-2 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      <div className="card p-4 space-y-4">
        <div className="flex items-center gap-4">
          <ProgressCircle value={lastResult?.score ?? 0} />
          <div className="text-sm text-slate-600">
            {lastResult?.score != null ? (
              <>
                <div>Score global: <span className="font-semibold">{lastResult.score}%</span></div>
                <div className="text-slate-500">Méthode: similarité Jaccard (tokens normalisés)</div>
              </>
            ) : (
              <div className="text-slate-500">Calculez pour voir le score…</div>
            )}
          </div>
        </div>

        {lastResult?.missingKeywords?.length > 0 && (
          <div>
            <div className="mb-2 text-sm font-medium text-slate-600">
              Mots-clés manquants
            </div>
            <div className="flex flex-wrap gap-2">
              {lastResult.missingKeywords.map((k) => (
                <span
                  key={k}
                  className="badge border-amber-200 bg-amber-50 text-amber-700"
                >
                  {k}
                </span>
              ))}
            </div>
          </div>
        )}

        {lastResult?.suggestions?.length > 0 && (
          <div>
            <div className="mb-2 text-sm font-medium text-slate-600">
              Suggestions pour s'améliorer
            </div>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
              {lastResult.suggestions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
