import React from "react";

function wordCount(t = "") { return t.trim() ? t.trim().split(/\s+/).length : 0; }

export default function QuickInsights({ cvText, jobText }) {
  const cvWords = wordCount(cvText);
  const jdWords = wordCount(jobText);

  return (
    <div id="insights" className="grid grid-cols-1 gap-4 sm:grid-cols-2 animate-fade-in">
      <div className="card p-4">
        <div className="text-sm text-slate-500">Longueur CV</div>
        <div className="mt-1 text-3xl font-semibold">{cvWords}</div>
        <div className="text-xs text-slate-400">mots</div>
      </div>
      <div className="card p-4">
        <div className="text-sm text-slate-500">Longueur JD</div>
        <div className="mt-1 text-3xl font-semibold">{jdWords}</div>
        <div className="text-xs text-slate-400">mots</div>
      </div>
    </div>
  );
}
