// src/components/assistant/AssistantCards.jsx
import React, { useState } from "react";
import useAssistantCards from "../../hooks/useAssistantCards";
import { User, FileText, Briefcase, RefreshCcw, Clock } from "lucide-react";

function Chip({ children }) {
  return (
    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-50 border border-slate-200">
      {children}
    </span>
  );
}

function Line({ children }) {
  return <li className="line-clamp-2">{children}</li>;
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-slate-200 p-3 bg-white shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <div className="h-6 w-6 rounded-md bg-slate-100" />
        <div className="h-4 w-40 rounded bg-slate-100" />
      </div>
      <div className="h-3 w-28 rounded bg-slate-100 mb-2" />
      <div className="flex gap-1.5 mb-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-5 w-14 rounded-full bg-slate-100" />
        ))}
      </div>
      <div className="space-y-1">
        <div className="h-3 w-full rounded bg-slate-100" />
        <div className="h-3 w-2/3 rounded bg-slate-100" />
      </div>
    </div>
  );
}

function Meta({ updatedAt }) {
  if (!updatedAt) return null;
  const d = new Date(updatedAt);
  return (
    <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-500">
      <Clock className="h-3.5 w-3.5" />
      <span>Maj {d.toLocaleDateString()} {d.toLocaleTimeString()}</span>
    </div>
  );
}

function MiniCard({
  icon,
  tone = "profile",
  titlePrefix = "",
  title,
  subtitle,
  chips = [],
  bullets = [],
  updatedAt,
  onOpen,
}) {
  const toneRing =
    tone === "profile"
      ? "ring-sky-100"
      : tone === "cv"
      ? "ring-purple-100"
      : "ring-amber-100";

  return (
    <button
      type="button"
      onClick={() => onOpen?.({ title, subtitle, chips, bullets, tone })}
      className={`group w-full h-full text-left rounded-xl border border-slate-200 p-3 bg-white/90 hover:bg-white shadow-sm hover:shadow-md transition-all cursor-pointer focus:outline-none focus-visible:ring-2 ${toneRing}`}
      aria-label={`Ouvrir la carte ${title}`}
    >
      <div className="mb-1 flex items-center gap-2 text-slate-700">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-slate-100">
          {icon}
        </div>
        <div className="text-sm font-semibold truncate" title={title}>
          {titlePrefix}
          {title}
        </div>
      </div>
      {subtitle && (
        <div className="text-xs text-slate-500 truncate" title={subtitle}>
          {subtitle}
        </div>
      )}

      {chips?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {chips.slice(0, 4).map((c, i) => (
            <Chip key={i}>{c}</Chip>
          ))}
          {chips.length > 4 && (
            <span className="text-[11px] text-slate-500">
              +{chips.length - 4}
            </span>
          )}
        </div>
      )}

      {bullets?.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-slate-700">
          {bullets.slice(0, 2).map((b, i) => (
            <Line key={i}>{b}</Line>
          ))}
        </ul>
      )}

      <Meta updatedAt={updatedAt} />

      <div className="mt-2 text-[11px] font-medium text-purple-700 group-hover:underline">
        Voir la fiche complète →
      </div>
    </button>
  );
}

function CardModal({ title, subtitle, chips = [], bullets = [], onClose, tone = "profile" }) {
  return (
    <div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full sm:max-w-2xl max-h-[85vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white shadow-xl"
      >
        <div
          className={`px-5 py-4 border-b ${
            tone === "profile"
              ? "bg-gradient-to-r from-sky-50 to-blue-50"
              : tone === "cv"
              ? "bg-gradient-to-r from-purple-50 to-pink-50"
              : "bg-gradient-to-r from-amber-50 to-orange-50"
          }`}
        >
          <div className="text-sm uppercase tracking-wide text-slate-600">
            {tone === "profile"
              ? "Profil utilisateur"
              : tone === "cv"
              ? "Résumé du CV"
              : "Résumé de l’offre"}
          </div>
          <div className="text-lg font-semibold text-slate-800 mt-0.5">
            {title}
          </div>
          {subtitle && <div className="text-sm text-slate-600">{subtitle}</div>}
        </div>

        <div className="px-5 py-4">
          {chips?.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {chips.map((c, i) => (
                <Chip key={i}>{c}</Chip>
              ))}
            </div>
          )}
          {bullets?.length > 0 && (
            <ul className="list-disc list-inside space-y-1.5 text-sm text-slate-700">
              {bullets.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex justify-end gap-2 px-5 py-3 border-t bg-slate-50 rounded-b-2xl">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-slate-50"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AssistantCards({ refreshKey = 0 }) {
  const { cards, loading, error, refresh } = useAssistantCards(refreshKey);
  const [modal, setModal] = useState(null);

  const hasAny = !!(cards?.profile || cards?.cv || cards?.job);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        {loading ? (
          <div className="text-sm text-slate-500">Chargement des cartes…</div>
        ) : (
          <div className="text-sm text-slate-500">
            {error ? (
              <span className="text-red-600">Assistant: {error}</span>
            ) : hasAny ? (
              "Vue d’ensemble générée automatiquement."
            ) : (
              "Uploade un CV ou colle une Job Description pour voir les résumés ici."
            )}
          </div>
        )}

        <button
          type="button"
          onClick={refresh}
          className="btn btn-outline"
          aria-label="Rafraîchir les cartes"
        >
          <RefreshCcw className="h-4 w-4" />
          Rafraîchir
        </button>
      </div>

      {/* Grille 3 colonnes responsive */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {loading && (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        )}

        {!loading && cards.profile && (
          <MiniCard
            icon={<User className="h-4 w-4" />}
            tone="profile"
            title={cards.profile.title}
            subtitle={cards.profile.subtitle}
            chips={cards.profile.chips}
            bullets={cards.profile.bullets}
            updatedAt={cards.profile.updatedAt}
            onOpen={(data) => setModal({ tone: "profile", ...data })}
          />
        )}

        {!loading && cards.cv && (
          <MiniCard
            icon={<FileText className="h-4 w-4" />}
            tone="cv"
            titlePrefix="CV — "
            title={cards.cv.title}
            subtitle={cards.cv.subtitle}
            chips={cards.cv.chips}
            bullets={cards.cv.bullets}
            updatedAt={cards.cv.updatedAt}
            onOpen={(data) => setModal({ tone: "cv", ...data })}
          />
        )}

        {!loading && cards.job && (
          <MiniCard
            icon={<Briefcase className="h-4 w-4" />}
            tone="job"
            titlePrefix="Offre — "
            title={cards.job.title}
            subtitle={cards.job.subtitle}
            chips={cards.job.chips}
            bullets={cards.job.bullets}
            updatedAt={cards.job.updatedAt}
            onOpen={(data) => setModal({ tone: "job", ...data })}
          />
        )}
      </div>

      {modal && (
        <CardModal
          tone={modal.tone}
          title={modal.title}
          subtitle={modal.subtitle}
          chips={modal.chips}
          bullets={modal.bullets}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}
