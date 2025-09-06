// src/pages/AssistantWorkspace.jsx
import React, { useState } from "react";
import Sidebar from "../components/layout/Sidebar";
import AssistantCards from "../components/assistant/AssistantCards";
import ChatSection from "../components/chat/ChatSection";

function Section({ id, title, desc, children, right }) {
  return (
    <section id={id} className="scroll-mt-24">
      <div className="flex items-end justify-between mb-3">
        <div>
          <h2 className="text-base font-semibold text-slate-800">{title}</h2>
          {desc && <p className="text-sm text-slate-500">{desc}</p>}
        </div>
        {right}
      </div>
      <div className="card p-4">{children}</div>
    </section>
  );
}

// 👉 placeholders légers pour upload/matching/quiz – remplace par tes vrais composants si tu en as
function UploadPanel() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-xl border border-slate-200 p-4">
        <h3 className="text-sm font-medium mb-1">Uploader un CV</h3>
        <p className="text-xs text-slate-500">Glisse un PDF/DOCX pour extraction + parsing.</p>
      </div>
      <div className="rounded-xl border border-slate-200 p-4">
        <h3 className="text-sm font-medium mb-1">Coller une Job Description</h3>
        <p className="text-xs text-slate-500">Colle ici l’offre pour l’analyser et créer la carte Job.</p>
      </div>
    </div>
  );
}

function MatchingPanel() {
  return (
    <div className="rounded-xl border border-slate-200 p-6 text-sm text-slate-600">
      Lance un matching pour obtenir le score + mots-clés manquants. (Connecté à <code>/api/match</code>)
    </div>
  );
}

function QuizPanel() {
  return (
    <div className="rounded-xl border border-slate-200 p-6 text-sm text-slate-600">
      Génère un quiz basé sur le CV/JD. (Connecté à <code>/api/quiz</code>)
    </div>
  );
}

export default function AssistantWorkspace() {
  const [collapsed, setCollapsed] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl p-4 md:p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[auto,1fr]">
          <Sidebar isCollapsed={collapsed} onToggle={() => setCollapsed(v => !v)} />

          <main className="space-y-8">
            {/* bandeau */}
            <div className="rounded-2xl bg-gradient-to-r from-purple-600 to-blue-600 p-5 text-white shadow-sm">
              <h1 className="text-xl font-semibold">Votre Assistant Recrutement</h1>
              <p className="text-sm text-purple-100/90">
                Résumés, matching, chat et quiz – tout est ici, rangé par sections.
              </p>
            </div>

            {/* Résumés Assistant */}
            <Section
              id="resume"
              title="Résumés (Profil / CV / Offre)"
              desc="Cartes générées automatiquement pour vous donner la vue d’ensemble."
              right={
                <button
                  className="btn btn-outline"
                  onClick={() => setRefreshKey(k => k + 1)}
                  aria-label="Rafraîchir les cartes"
                >
                  Rafraîchir
                </button>
              }
            >
              <AssistantCards refreshKey={refreshKey} />
            </Section>

            {/* Upload & Parsing */}
            <Section
              id="upload"
              title="Upload & Parsing"
              desc="Uploade un CV ou colle une offre pour alimenter l’assistant."
            >
              <UploadPanel />
            </Section>

            {/* Matching */}
            <Section
              id="matching"
              title="Scoring (Matching CV ↔ Offre)"
              desc="Compare le CV et la Job Description pour obtenir un score et des suggestions."
            >
              <MatchingPanel />
            </Section>

            {/* Chat */}
            <Section
              id="chat"
              title="Chat IA (Vira)"
              desc="Pose des questions contextuelles (CV/JD) à l’assistant."
            >
              <ChatSection refreshKey={refreshKey} />
            </Section>

            {/* Quiz */}
            <Section
              id="quiz"
              title="Quiz IA (Gemini)"
              desc="Génère et évalue des quiz techniques adaptés au profil."
            >
              <QuizPanel />
            </Section>
          </main>
        </div>
      </div>
    </div>
  );
}
