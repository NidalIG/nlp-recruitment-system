import React, { useEffect, useMemo, useRef, useState } from "react";
import { Send, Loader2, Bot, User, Trash2, Copy, Check } from "lucide-react";

export default function ChatSection({
  apiUrl = "/api/chat",
  systemPrompt = "Tu es un assistant utile spécialisé en recrutement : tu aides à analyser des CV et des offres d'emploi, et tu réponds en français de façon claire et concise.",
}) {
  const [messages, setMessages] = useState([
    {
      id: crypto.randomUUID(),
      role: "assistant",
      content:
        "Bonjour ! Je suis votre assistant IA. Si vous voulez un **quiz**, rendez-vous à la section *Quiz IA (Gemini)* ci-dessous.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copiedId, setCopiedId] = useState(null);
  const listRef = useRef(null);
  const inputRef = useRef(null);

  const apiMessages = useMemo(() => {
    return [
      { role: "system", content: systemPrompt },
      ...messages.map(({ role, content }) => ({ role, content })),
    ];
  }, [messages, systemPrompt]);

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
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...apiMessages, { role: "user", content: trimmed }] }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`);
      const ai = data?.message || data?.reply || data?.choices?.[0]?.message;
      const content = ai?.content || "(Réponse vide)";
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content },
      ]);
    } catch (e) {
      setError("Impossible d'obtenir une réponse de l'IA.");
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function onSubmit(e) { e.preventDefault(); void sendMessage(input); }
  function handleKeyDown(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void sendMessage(input); } }
  function clearChat() { setMessages([{ id: crypto.randomUUID(), role: "assistant", content: "Nouveau chat." }]); setError(""); inputRef.current?.focus(); }
  async function copyMessage(id, text) { try { await navigator.clipboard.writeText(text); setCopiedId(id); setTimeout(() => setCopiedId(null), 1200); } catch (_) {} }

  return (
    <div id="chat" className="flex h-[480px] w-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft animate-fade-in">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 p-3 md:p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600/10">
            <Bot className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-sm font-semibold leading-tight md:text-base">Assistant IA</h2>
            <p className="text-xs text-slate-500">Chat</p>
          </div>
        </div>
        <button
          onClick={clearChat}
          className="btn btn-outline"
          title="Effacer la conversation"
        >
          <Trash2 className="h-4 w-4" />
          Réinitialiser
        </button>
      </div>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-3 md:p-4">
        {messages.map((m) => (
          <MessageBubble key={m.id} m={m} onCopy={copyMessage} copiedId={copiedId} />
        ))}
        {loading && (
          <div className="flex items-start gap-2">
            <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-full bg-blue-600/10">
              <Bot className="h-4 w-4 text-blue-600" />
            </div>
            <div className="max-w-[85%] rounded-2xl rounded-tl-none border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-slate-700">
              <div className="flex items-center gap-2 text-blue-700">
                <Loader2 className="h-4 w-4 animate-spin" />
                L'IA rédige une réponse...
              </div>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mx-3 mb-2 rounded-2xl border border-red-200 bg-red-50 p-2 text-xs text-red-700 md:mx-4">
          {error}
        </div>
      )}

      <form onSubmit={onSubmit} className="border-t border-slate-200 p-3 md:p-4">
        <div className="flex items-end gap-2">
          <div className="mb-1 hidden h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white sm:flex">
            <User className="h-4 w-4" />
          </div>
          <div className="relative w-full">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Écrivez votre message. Shift+Entrée = nouvelle ligne"
              className="input max-h-40 resize-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn btn-primary disabled:cursor-not-allowed disabled:opacity-50"
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

function MessageBubble({ m, onCopy, copiedId }) {
  const isUser = m.role === "user";
  return (
    <div className={`flex items-start gap-2 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600/10">
          <Bot className="h-4 w-4 text-blue-600" />
        </div>
      )}

      <div
        className={`group relative max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm shadow-soft ${
          isUser ? "rounded-tr-none bg-slate-900 text-white" : "rounded-tl-none border border-slate-200 bg-white text-slate-800"
        }`}
      >
        {m.content}
        {!isUser && (
          <button
            onClick={() => onCopy(m.id, m.content)}
            className={`absolute -right-2 -top-2 hidden rounded-full border bg-white p-1 text-slate-500 shadow-soft transition hover:text-slate-700 group-hover:inline-flex ${
              copiedId === m.id ? "border-green-200 bg-green-50" : "border-slate-200"
            }`}
            title="Copier"
          >
            {copiedId === m.id ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
