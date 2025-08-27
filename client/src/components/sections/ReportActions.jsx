import React, { useState } from "react";

export default function ReportActions({ cvText, jobText, result }) {
  const [downloading, setDownloading] = useState(false);
  const canDownload = result?.score != null && (cvText?.trim() || jobText?.trim());

  async function downloadPdf() {
    setDownloading(true);
    try {
      const res = await fetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cvText, jobText,
          score: result?.score ?? 0,
          missingKeywords: result?.missingKeywords ?? [],
          suggestions: result?.suggestions ?? [],
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "rapport-matching.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Téléchargement impossible. Vérifiez le serveur /api/report.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div id="report" className="card p-4 animate-fade-in">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-slate-600">
          Exporter un PDF récapitulatif (CV + JD + score + recommandations).
        </div>
        <button
          onClick={downloadPdf}
          disabled={!canDownload || downloading}
          className="btn btn-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          {downloading ? "Génération…" : "Télécharger le rapport PDF"}
        </button>
      </div>
    </div>
  );
}
