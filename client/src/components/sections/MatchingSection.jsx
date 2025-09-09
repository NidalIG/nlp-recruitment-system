import React, { useState } from "react";
import ProgressCircle from "../ui/ProgressCircle.jsx";

export default function MatchingSection({ parsedCv, lastResult }) {
  const [showDetails, setShowDetails] = useState(false);

  // On utilise directement lastResult passé en props au lieu du hook
  if (!lastResult) return null;

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
  const scoreColorHex = (s = 0) => {
  if (s >= 80) return '#22c55e'; // green-500
  if (s >= 50) return '#f59e0b'; // amber-500
  return '#ef4444';              // red-500
};

  return (
    <div className="space-y-4 animate-fade-in">
      <h2 className="text-xl font-bold text-slate-800 text-center">Résultats de l'analyse</h2>

      


<div className={`card p-6 space-y-4 ${getScoreBackground(lastResult?.score)}`}>
  <div className="flex items-center justify-center gap-6">
    <ProgressCircle
      value={lastResult?.score ?? 0}
      textColor={scoreColorHex(lastResult?.score ?? 0)} // <-- ICI
      // textClass="tracking-tight" // (optionnel pour du style en plus)
    />
    <div className="text-center">
      {/* On n’affiche plus le score ici pour éviter le doublon */}
      <div className="text-lg font-semibold text-slate-700">
        {lastResult?.similarity_level}
      </div>
      {/* <div className="text-slate-500 text-sm mt-1">
        {lastResult?.method || 'Similarité par embedding'}
      </div> */}
    </div>
  </div>



        {/* Scores sectionnels */}
        {lastResult.sectional_scores && Object.keys(lastResult.sectional_scores).length > 0 && (
          <div>
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full mb-3 text-sm font-medium text-slate-600 hover:text-slate-800 flex items-center justify-center gap-2"
            >
              Scores détaillés {showDetails ? "▼" : "▶"}
            </button>
            {showDetails && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {["global", "skills", "experience", "education"].map((key) => (
                  <div key={key} className="text-center p-3 bg-white rounded-lg border">
                    <div className="font-semibold text-slate-700">{key.charAt(0).toUpperCase() + key.slice(1)}</div>
                    <div className={`text-2xl font-bold ${
                      key === "global" ? "text-blue-600" :
                      key === "skills" ? "text-green-600" :
                      key === "experience" ? "text-purple-600" : "text-indigo-600"
                    }`}>
                      {lastResult.sectional_scores[key] || 0}%
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Analyse compétences */}
        {lastResult.skill_analysis && Object.keys(lastResult.skill_analysis).length > 0 && (
          <div className="bg-white p-4 rounded-lg border">
            <div className="mb-3 text-base font-semibold text-slate-700">Analyse des compétences</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="flex justify-between">
                <span>Similarité moyenne:</span>
                <strong className="text-blue-600">
                  {lastResult.skill_analysis.average_skill_similarity || 0}%
                </strong>
              </div>
              <div className="flex justify-between">
                <span>Couverture:</span>
                <strong className="text-green-600">
                  {lastResult.skill_analysis.skill_coverage || 0}%
                </strong>
              </div>
            </div>

            {lastResult.skill_analysis.top_skill_matches?.length > 0 && showDetails && (
              <div className="mt-4">
                <div className="text-sm text-slate-600 mb-2">Top correspondances:</div>
                <div className="space-y-2">
                  {lastResult.skill_analysis.top_skill_matches.slice(0, 3).map((match, i) => (
                    <div key={i} className="text-sm bg-slate-50 p-2 rounded flex justify-between">
                      <span><strong>{match.job_skill}</strong> → {match.matched_cv_skill}</span>
                      <span className="text-green-600 font-semibold">
                        {Math.round((match.similarity || 0) * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Compétences à développer */}
        {lastResult.missing_keywords?.length > 0 && (
          <div className="bg-white p-4 rounded-lg border">
            <div className="mb-3 text-base font-semibold text-slate-700">Compétences à développer</div>
            <div className="flex flex-wrap gap-2">
              {lastResult.missing_keywords.slice(0, 12).map((keyword, i) => (
                <span key={i} className="badge border-amber-200 bg-amber-50 text-amber-700 px-3 py-1">
                  {keyword}
                </span>
              ))}
              {lastResult.missing_keywords.length > 12 && (
                <span className="text-sm text-slate-500 px-2">
                  +{lastResult.missing_keywords.length - 12} autres...
                </span>
              )}
            </div>
          </div>
        )}

        {/* Suggestions */}
        {lastResult.suggestions?.length > 0 && (
          <div className="bg-white p-4 rounded-lg border">
            <div className="mb-3 text-base font-semibold text-slate-700">Suggestions d'amélioration</div>
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
              {lastResult.suggestions.map((suggestion, i) => (
                <li key={i}>{suggestion}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}