import React, { useEffect, useMemo, useRef, useState } from "react";
import { Send, Loader2, Bot, User, Trash2, Copy, Check, MessageSquare } from "lucide-react";

export default function ChatSection({
  apiUrl = "/api/chat",
  systemPrompt = "Tu es un assistant utile spécialisé en recrutement : tu aides à analyser des CV et des offres d'emploi, et tu réponds en français de façon claire et concise.",
}) {
  const [messages, setMessages] = useState([
    {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "Bonjour ! Je suis votre assistant IA spécialisé en recrutement. Comment puis-je vous aider aujourd'hui ?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copiedId, setCopiedId] = useState(null);

  const listRef = useRef(null);
  const inputRef = useRef(null);

  // Messages formatés pour l'API
  const apiMessages = useMemo(() => [
    { role: "system", content: systemPrompt },
    ...messages.map(({ role, content }) => ({ role, content }))
  ], [messages, systemPrompt]);

  // Scroll automatique vers le bas
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed) return;

    setError("");
    setLoading(true);
    const userMsg = { id: crypto.randomUUID(), role: "user", content: trimmed };
    setMessages(prev => [...prev, userMsg]);
    setInput("");

    try {
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...apiMessages, { role: "user", content: trimmed }] }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`);

      const content = data?.message?.content || data?.reply || data?.choices?.[0]?.message?.content || "(Réponse vide)";
      setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "assistant", content }]);
    } catch (e) {
      setError("Impossible d'obtenir une réponse de l'IA.");
      console.error(e);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  // Handlers
  function onSubmit(e) { e.preventDefault(); void sendMessage(input); }
  function handleKeyDown(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void sendMessage(input); } }
  function clearChat() { 
    setMessages([{ id: crypto.randomUUID(), role: "assistant", content: "Nouveau chat démarré ! Comment puis-je vous aider ?" }]);
    setError(""); 
    inputRef.current?.focus(); 
  }
  async function copyMessage(id, text) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1200);
    } catch (_) {}
  }

  return (
    <div className="h-[600px] w-full flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-gradient-to-r from-purple-600 to-blue-600 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20">
            <MessageSquare className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-base font-semibold leading-tight text-white">Ask Vira</h2>
            <p className="text-xs text-purple-100">Votre Virtual AI Recruiter</p>
          </div>
        </div>
        <button onClick={clearChat} className="flex items-center gap-2 rounded-lg bg-white/20 px-3 py-2 text-xs text-white hover:bg-white/30 transition-colors" title="Nouveau chat">
          <Trash2 className="h-4 w-4" /> Nouveau
        </button>
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-gradient-to-b from-purple-50/30 to-blue-50/30 p-4">
        {messages.map(m => <MessageBubble key={m.id} m={m} onCopy={copyMessage} copiedId={copiedId} />)}
        {loading && (
          <div className="flex items-start gap-3">
            <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-r from-purple-600/10 to-blue-600/10">
              <Bot className="h-5 w-5 text-purple-600" />
            </div>
            <div className="max-w-[80%] rounded-2xl rounded-tl-none border border-purple-100 bg-gradient-to-r from-purple-50 to-blue-50 px-4 py-3 text-sm text-slate-700">
              <div className="flex items-center gap-2 text-purple-700">
                <Loader2 className="h-4 w-4 animate-spin" /> Vira rédige une réponse...
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && <div className="mx-4 mb-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">❌ {error}</div>}

      {/* Input */}
      <form onSubmit={onSubmit} className="border-t border-slate-200 bg-white p-4">
        <div className="flex items-end gap-3">
          <div className="mb-1 hidden h-9 w-9 items-center justify-center rounded-full bg-gradient-to-r from-slate-800 to-slate-900 text-white sm:flex">
            <User className="h-4 w-4" />
          </div>
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Posez votre question à Vira..."
              className="w-full resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-100"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50 hover:shadow-lg transition-all"
            aria-label="Envoyer"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span className="hidden sm:inline">Envoyer</span>
          </button>
        </div>
      </form>
    </div>
  );
}

// Composant Message
function MessageBubble({ m, onCopy, copiedId }) {
  const isUser = m.role === "user";
  return (
    <div className={`flex items-start gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-purple-600/10 to-blue-600/10"><Bot className="h-5 w-5 text-purple-600" /></div>}
      <div className={`group relative max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm shadow-sm ${isUser ? "rounded-tr-none bg-gradient-to-r from-slate-800 to-slate-900 text-white" : "rounded-tl-none border border-slate-200 bg-white text-slate-800"}`}>
        {m.content}
        {!isUser && (
          <button onClick={() => onCopy(m.id, m.content)} className={`absolute -right-2 -top-2 hidden rounded-full border bg-white p-1.5 text-slate-500 shadow-sm transition hover:text-slate-700 group-hover:inline-flex ${copiedId === m.id ? "border-green-200 bg-green-50" : "border-slate-200"}`} title="Copier">
            {copiedId === m.id ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
      {isUser && <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-slate-800 to-slate-900 text-white"><User className="h-5 w-5" /></div>}
    </div>
  );
}
