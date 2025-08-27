import React, { useRef, useState } from "react";

export default function UploadSection({ cvText, setCvText, setFilename }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const inputRef = useRef(null);

  // URL absolue du backend en dev, sinon relative en prod
  const API_BASE =
    import.meta.env.VITE_API_BASE ||
    (window.location.hostname === "localhost" ? "http://localhost:3001" : "");

  async function onFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validation côté client (le serveur filtrera aussi)
    const okTypes = ["application/pdf", "text/plain"];
    const isOk =
      okTypes.includes(file.type) ||
      /\.pdf$/i.test(file.name) ||
      /\.txt$/i.test(file.name);
    if (!isOk) {
      setError("Type non supporté. Choisis un PDF ou un TXT.");
      e.target.value = "";
      return;
    }

    setError("");
    setWarning("");
    setLoading(true);

    try {
      const form = new FormData();
      form.append("file", file);

      // Timeout pour éviter les attentes infinies
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 25000);

      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      clearTimeout(timer);

      // Lecture robuste (toujours JSON côté serveur, mais on protège)
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      let data;
      try {
        if (ct.includes("application/json")) {
          data = await res.json();
        } else {
          data = JSON.parse(await res.text());
        }
      } catch {
        throw new Error(
          `Réponse invalide du serveur. Vérifie que l'API tourne sur ${API_BASE}`
        );
      }

      if (!res.ok) {
        throw new Error(data?.error || `Upload/parse échoué (HTTP ${res.status})`);
      }

      setCvText(data.text || "");
      setFilename?.(data.filename || file.name);

      // Affiche une alerte "jaune" si le texte est vide/scanné
      const warn =
        data.warning_human ||
        data.warning ||
        (!data.text ? "Aucun texte détecté. PDF scanné ? Utilise un PDF texte ou passe par un OCR." : "");
      if (warn) setWarning(warn);
    } catch (err) {
      const msg =
        err?.name === "AbortError"
          ? "Délai dépassé. Assure-toi que le serveur est lancé."
          : err?.message || "Échec d'upload/parse.";
      setError(msg);
      // Permettre de re-sélectionner le même fichier après erreur
      if (inputRef.current) inputRef.current.value = "";
    } finally {
      setLoading(false);
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
          accept=".pdf,.txt,application/pdf,text/plain"
          onChange={onFile}
          className="input file:mr-3 file:rounded-md file:border-0 file:bg-slate-900 file:px-3 file:py-2 file:text-white hover:file:bg-slate-800"
        />
        {loading && <span className="text-sm text-slate-500">Extraction…</span>}
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {warning && !error && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-2 text-sm text-amber-800">
          {warning}
        </div>
      )}

      <div className="card p-4">
        <label className="mb-2 block text-sm font-medium text-slate-600">
          Texte extrait du CV
        </label>
        <textarea
          value={cvText}
          onChange={(e) => setCvText(e.target.value)}
          rows={10}
          placeholder="Le texte du CV sera affiché ici après l'upload..."
          className="input"
        />
      </div>
    </div>
  );
}
