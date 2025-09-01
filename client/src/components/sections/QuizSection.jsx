import React, { useMemo, useState } from "react";
import { Sparkles, CheckCircle2, XCircle, Loader2, Trophy, Target, BookOpen, AlertCircle } from "lucide-react";

export default function QuizSection() {
  const [level, setLevel] = useState("facile");
  const [count, setCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [quizInfo, setQuizInfo] = useState(null);
  const [showResults, setShowResults] = useState(false);

  async function generate() {
    setLoading(true); 
    setError(""); 
    setResult(null); 
    setAnswers({}); 
    setQuestions([]);
    setShowResults(false);
    setQuizInfo(null);

    try {
      const res = await fetch("/api/quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, count: parseInt(count) }),
      });
      
      const ct = res.headers.get("content-type") || "";
      const data = ct.includes("application/json") ? await res.json() : {};
      
      if (!res.ok) {
        throw new Error(data?.error || "Génération du quiz impossible");
      }

      if (!data.questions || data.questions.length === 0) {
        throw new Error("Aucune question générée");
      }

      setQuestions(data.questions || []);
      setQuizInfo(data.quiz_info || null);
      
    } catch (e) {
      setError(e.message || "Erreur lors de la génération du quiz");
      console.error("Erreur quiz:", e);
    } finally {
      setLoading(false);
    }
  }

  function choose(qid, idx) {
    setAnswers(a => ({ ...a, [qid]: idx }));
  }

  async function correct() {
    if (!questions.length) return;

    try {
      setLoading(true);
      
      // Évaluation locale simple pour l'instant
      let score = 0;
      const details = questions.map(q => {
        const ok = q.answerIndex === answers[q.id];
        if (ok) score += 1;
        return { 
          id: q.id, 
          ok, 
          expected: q.answerIndex, 
          got: answers[q.id],
          question: q.question,
          explanation: q.explanation,
          skillArea: q.skillArea
        };
      });

      const percentage = (score / questions.length * 100);
      
      setResult({ 
        score, 
        total: questions.length, 
        details,
        percentage: Math.round(percentage * 10) / 10,
        feedback: generateLocalFeedback(percentage, details)
      });
      setShowResults(true);

    } catch (e) {
      setError("Erreur lors de la correction: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  function generateLocalFeedback(percentage, details) {
    let level, message, color;
    
    if (percentage >= 80) {
      level = "Excellent";
      message = "Félicitations ! Vous maîtrisez très bien le sujet.";
      color = "green";
    } else if (percentage >= 60) {
      level = "Bien"; 
      message = "Bon travail ! Quelques points à revoir mais vous êtes sur la bonne voie.";
      color = "blue";
    } else if (percentage >= 40) {
      level = "Moyen";
      message = "Il y a des lacunes à combler. Continuez à étudier !";
      color = "orange";
    } else {
      level = "À améliorer";
      message = "Il faut revoir les bases. Ne vous découragez pas !";
      color = "red";
    }

    return { level, message, color, percentage };
  }

  function resetQuiz() {
    setQuestions([]);
    setAnswers({});
    setResult(null);
    setShowResults(false);
    setQuizInfo(null);
    setError("");
  }

  const disabled = loading;
  const allAnswered = questions.length > 0 && questions.every(q => answers[q.id] !== undefined);

  return (
    <div id="quiz" className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-indigo-600" />
        <h2 className="text-base font-semibold text-slate-800">Quiz IA Personnalisé</h2>
      </div>

      {/* Configuration du Quiz - Cachée quand quiz ou résultats affichés */}
      {questions.length === 0 && !showResults && (
        <div className="card p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium text-slate-700">Niveau</label>
              <select 
                value={level} 
                onChange={e => setLevel(e.target.value)} 
                className="input mt-1"
                disabled={disabled}
              >
                <option value="facile">Facile - Débutant</option>
                <option value="moyen">Moyen - Intermédiaire</option>
                <option value="difficile">Difficile - Avancé</option>
              </select>
            </div>
            
            <div>
              <label className="text-sm font-medium text-slate-700">Questions</label>
              <select 
                value={count} 
                onChange={e => setCount(Number(e.target.value))} 
                className="input mt-1"
                disabled={disabled}
              >
                <option value="5">5 questions</option>
                <option value="10">10 questions</option>
                <option value="15">15 questions</option>
              </select>
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <button 
              onClick={generate} 
              disabled={disabled} 
              className="btn btn-primary disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> 
                  Génération...
                </>
              ) : (
                <>
                  <Target className="h-4 w-4" />
                  Générer le quiz
                </>
              )}
            </button>
            
            <button 
              onClick={resetQuiz} 
              className="btn btn-outline flex items-center gap-2"
              disabled={loading}
            >
              Réinitialiser
            </button>
          </div>

          {error && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}
        </div>
      )}

      {/* Message d'erreur affiché même quand la configuration est cachée */}
      {(questions.length > 0 || showResults) && error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
          <div className="text-sm text-red-700">{error}</div>
        </div>
      )}

      {/* Informations du Quiz */}
      {quizInfo && (
        <div className="card p-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200">
          <h3 className="font-semibold text-indigo-900 mb-2">{quizInfo.title}</h3>
          <p className="text-sm text-indigo-700 mb-2">{quizInfo.description}</p>
          <div className="flex items-center gap-4 text-xs text-indigo-600">
            <span className="flex items-center gap-1">
              <BookOpen className="h-3 w-3" />
              {quizInfo.estimated_duration} min
            </span>
            <span>Niveau: {level}</span>
          </div>
        </div>
      )}

      {/* Questions du Quiz */}
      {questions?.length > 0 && !showResults && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">
              Questions ({questions.length})
            </h3>
            <div className="text-sm text-slate-600">
              Répondu: {Object.keys(answers).length}/{questions.length}
            </div>
          </div>

          {questions.map((q, i) => (
            <div key={q.id} className="card p-4 hover:shadow-md transition-shadow">
              <div className="mb-3 text-sm font-medium text-slate-800">
                <span className="inline-block bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-xs mr-2">
                  Q{i + 1}
                </span>
                {q.question}
              </div>
              
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {q.choices.map((c, idx) => {
                  const active = answers[q.id] === idx;
                  return (
                    <button 
                      key={idx} 
                      onClick={() => choose(q.id, idx)} 
                      className={`text-left p-3 rounded-lg border transition-all ${
                        active 
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-md' 
                          : 'bg-white hover:bg-indigo-50 border-slate-200 hover:border-indigo-300'
                      }`}
                    >
                      <span className="font-medium">{String.fromCharCode(65 + idx)}</span> {c}
                    </button>
                  );
                })}
              </div>

              {q.skillArea && (
                <div className="mt-2 text-xs text-slate-500">
                  Compétence: {q.skillArea}
                </div>
              )}
            </div>
          ))}

          <div className="flex items-center justify-between gap-4 p-4 bg-slate-50 rounded-lg">
            <div className="text-sm text-slate-600">
              {allAnswered ? (
                <span className="text-green-600 font-medium">✓ Toutes les questions ont été répondues</span>
              ) : (
                <span>Répondez à toutes les questions avant de corriger</span>
              )}
            </div>
            <button 
              onClick={correct} 
              disabled={!allAnswered || loading}
              className="btn btn-primary disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Corriger le quiz
            </button>
          </div>
        </div>
      )}

      {/* Résultats */}
      {result && showResults && (
        <div className="space-y-4">
          {/* Score Global */}
          <div className="card p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
            <div className="flex items-center gap-3 mb-4">
              <Trophy className={`h-6 w-6 ${
                result.feedback.color === 'green' ? 'text-green-600' :
                result.feedback.color === 'blue' ? 'text-blue-600' :
                result.feedback.color === 'orange' ? 'text-orange-600' :
                'text-red-600'
              }`} />
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Résultat: {result.feedback.level}
                </h3>
                <p className="text-sm text-slate-600">{result.feedback.message}</p>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="text-2xl font-bold text-slate-900">
                {result.score}/{result.total}
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-indigo-600">
                  {result.percentage}%
                </div>
                <div className="text-xs text-slate-500">Score final</div>
              </div>
            </div>
          </div>

          {/* Détail des Questions */}
          <div className="space-y-3">
            <h4 className="font-semibold text-slate-800">Détail des réponses</h4>
            
            {questions.map((q, i) => {
              const detail = result.details.find(d => d.id === q.id);
              const isCorrect = detail?.ok;
              
              return (
                <div key={q.id} className="card p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="text-sm font-medium text-slate-800">
                      Q{i + 1}. {q.question}
                    </div>
                    {isCorrect ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                  </div>

                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 mb-3">
                    {q.choices.map((c, idx) => {
                      const isUserAnswer = answers[q.id] === idx;
                      const isCorrectAnswer = q.answerIndex === idx;
                      
                      let bgColor = 'bg-slate-50';
                      let textColor = 'text-slate-700';
                      let borderColor = 'border-slate-200';
                      
                      if (isCorrectAnswer) {
                        bgColor = 'bg-green-100';
                        textColor = 'text-green-800';
                        borderColor = 'border-green-300';
                      } else if (isUserAnswer && !isCorrect) {
                        bgColor = 'bg-red-100';
                        textColor = 'text-red-800';
                        borderColor = 'border-red-300';
                      }
                      
                      return (
                        <div 
                          key={idx} 
                          className={`p-2 rounded border ${bgColor} ${textColor} ${borderColor}`}
                        >
                          <span className="font-medium">{String.fromCharCode(65 + idx)}</span> {c}
                          {isCorrectAnswer && <span className="ml-2">✓</span>}
                          {isUserAnswer && !isCorrectAnswer && <span className="ml-2">✗</span>}
                        </div>
                      );
                    })}
                  </div>

                  {q.explanation && (
                    <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded border-l-4 border-blue-400">
                      <strong>Explication:</strong> {q.explanation}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex gap-2">
            <button onClick={resetQuiz} className="btn btn-primary">
              Nouveau quiz
            </button>
            <button onClick={() => setShowResults(false)} className="btn btn-outline">
              Revoir les questions
            </button>
          </div>
        </div>
      )}
    </div>
  );
}