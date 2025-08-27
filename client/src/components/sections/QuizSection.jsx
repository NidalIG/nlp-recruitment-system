import React, { useMemo, useState } from "react";
import { Sparkles, CheckCircle2, XCircle, Loader2 } from "lucide-react";

export default function QuizSection() {
  const [level, setLevel] = useState("facile");
  const [count, setCount] = useState(5);
  const [topic, setTopic] = useState("Développement web");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);

  async function generate() {
    setLoading(true); setError(""); setResult(null); setAnswers({}); setQuestions([]);
    try {
      const res = await fetch("/api/quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, count, topic }),
      });
      const ct = res.headers.get("content-type") || "";
      const data = ct.includes("application/json") ? await res.json() : {};
      if (!res.ok) throw new Error(data?.error || "Génération du quiz impossible");
      setQuestions(data.questions || []);
    } catch (e) {
      setError(e.message || "Erreur quiz");
    } finally {
      setLoading(false);
    }
  }

  function choose(qid, idx) {
    setAnswers(a => ({ ...a, [qid]: idx }));
  }

  function correct() {
    let score = 0;
    const details = questions.map(q => {
      const ok = q.answerIndex === answers[q.id];
      if (ok) score += 1;
      return { id: q.id, ok, expected: q.answerIndex, got: answers[q.id] };
    });
    setResult({ score, total: questions.length, details });
  }

  const disabled = loading;

  return (
    <div id="quiz" className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-indigo-600" />
        <h2 className="text-base font-semibold text-slate-800">Quiz IA (Gemini)</h2>
      </div>

      <div className="card p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="text-sm text-slate-600">Niveau</label>
            <select value={level} onChange={e=>setLevel(e.target.value)} className="input">
              <option value="facile">Facile</option>
              <option value="moyen">Moyen</option>
              <option value="difficile">Difficile</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-600">Nombre de questions</label>
            <select value={count} onChange={e=>setCount(Number(e.target.value))} className="input">
              <option value="5">5</option>
              <option value="10">10</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-600">Thème</label>
            <input value={topic} onChange={e=>setTopic(e.target.value)} className="input" placeholder="ex. JavaScript, DevOps, SQL..." />
          </div>
        </div>
        <div className="mt-3 flex gap-2">
          <button onClick={generate} disabled={disabled} className="btn btn-primary disabled:opacity-50">{loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Génération…</> : "Générer le quiz"}</button>
          <button onClick={()=>{setQuestions([]); setAnswers({}); setResult(null);}} className="btn btn-outline">Réinitialiser</button>
        </div>
        {error && <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 p-2 text-sm text-red-700">{error}</div>}
      </div>

      {questions?.length>0 && (
        <div className="space-y-3">
          {questions.map((q, i) => (
            <div key={q.id} className="card p-4">
              <div className="mb-2 text-sm font-medium text-slate-700">Q{i+1}. {q.question}</div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {q.choices.map((c, idx) => {
                  const active = answers[q.id] === idx;
                  return (
                    <button key={idx} onClick={()=>choose(q.id, idx)} className={`text-left btn ${active ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'btn-outline'}`}>
                      {c}
                    </button>
                  )
                })}
              </div>
              {result && (
                <div className="mt-2 text-sm">
                  {result.details.find(d=>d.id===q.id)?.ok ? (
                    <span className="inline-flex items-center gap-1 text-green-700"><CheckCircle2 className="h-4 w-4"/>Correct</span>
                  ) : answers[q.id]!=null ? (
                    <span className="inline-flex items-center gap-1 text-red-700"><XCircle className="h-4 w-4"/>Incorrect</span>
                  ) : null}
                  {q.explanation && <div className="mt-1 text-slate-600">{q.explanation}</div>}
                </div>
              )}
            </div>
          ))}
          <div className="flex items-center gap-2">
            <button onClick={correct} className="btn btn-primary">Corriger</button>
            {result && <div className="text-sm text-slate-700">Score: <span className="font-semibold">{result.score}/{result.total}</span></div>}
          </div>
        </div>
      )}
    </div>
  );
}
