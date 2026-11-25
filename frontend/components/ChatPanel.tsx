"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

// SA-36 / SA-37 — interface de chat branchée sur l'API /api/v1/chat (dialogue multi-tours avec le LLM).

type Sender = "user" | "assistant";
type ChatMessage = { sequence: number; sender: Sender; content: string; detected_language: string };
type Memory = { profile: Record<string, string | string[]>; asked_questions: string[]; language: string | null; turns: number };
type ChatReply = { user_message: ChatMessage; reply: ChatMessage; memory: Memory; model: string; latency_ms: number };

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "smartcampus.chat.session";

const LANGUAGES: Record<string, string> = {
  fr: "Français",
  ar: "Arabe",
  tn_darija: "Tunisien",
  arabizi: "Arabizi",
  en: "Anglais",
  mixed: "Mélange",
  unknown: "?",
};

const PROFILE_LABELS: Record<string, string> = {
  niveau: "Niveau",
  section_bac: "Section du bac",
  moyenne: "Moyenne",
  interets: "Centres d'intérêt",
  preferences: "Préférences",
  contraintes: "Contraintes",
  objectif: "Projet",
  formations_evoquees: "Formations évoquées",
};

const EXAMPLES = [
  "Bonjour, quelles formations proposez-vous à l'IIT ?",
  "aslema, 9rit bac maths w jebt 15, chnowa tnasa7ni ?",
  "قداش الفلوس متاع البريبا ؟",
];

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body?.error?.message ?? `Erreur ${res.status}`;
  } catch {
    return `Erreur ${res.status}`;
  }
}

export default function ChatPanel() {
  const [token, setToken] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memory, setMemory] = useState<Memory | null>(null);
  const [meta, setMeta] = useState<{ model: string; latency_ms: number } | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const startSession = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/chat/sessions`, { method: "POST" });
      if (!res.ok) throw new Error(await errorMessage(res));
      const body = await res.json();
      localStorage.setItem(TOKEN_KEY, body.session_token);
      setToken(body.session_token);
      setMessages([]);
      setMemory(null);
      setMeta(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "API non joignable.");
    }
  }, []);

  // Reprise de la conversation après rechargement de la page (historique + mémoire lus dans l'API).
  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) {
      void startSession();
      return;
    }
    const headers = { "X-Session-Token": saved };
    Promise.all([
      fetch(`${API_URL}/api/v1/chat/messages`, { headers }),
      fetch(`${API_URL}/api/v1/chat/memoire`, { headers }),
    ])
      .then(async ([h, m]) => {
        if (!h.ok || !m.ok) throw new Error("session expirée");
        setToken(saved);
        setMessages((await h.json()).messages);
        setMemory(await m.json());
      })
      .catch(() => void startSession());
  }, [startSession]);

  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, sending]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || !token || sending) return;
    setSending(true);
    setError(null);
    setInput("");
    const pending: ChatMessage = { sequence: -1, sender: "user", content, detected_language: "unknown" };
    setMessages((prev) => [...prev, pending]);
    try {
      const res = await fetch(`${API_URL}/api/v1/chat/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Session-Token": token },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error(await errorMessage(res));
      const body: ChatReply = await res.json();
      setMessages((prev) => [...prev.filter((m) => m !== pending), body.user_message, body.reply]);
      setMemory(body.memory);
      setMeta({ model: body.model, latency_ms: body.latency_ms });
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m !== pending));
      setInput(content);
      setError(e instanceof Error ? e.message : "Erreur réseau.");
    } finally {
      setSending(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  const profile = Object.entries(memory?.profile ?? {});

  return (
    <div className="chat-layout">
      <section className="chat-card" aria-label="Conversation avec l'assistant">
        <div className="preview-top">
          <span className="preview-avatar">AI</span>
          <div>
            <b>Assistant SmartCampus</b>
            <small>Français · Tunisien · Arabizi</small>
          </div>
          <button className="status-button chat-reset" type="button" onClick={() => void startSession()}>
            Nouvelle conversation
          </button>
        </div>

        <div className="chat-messages" aria-live="polite">
          {messages.length === 0 && !sending && (
            <div className="chat-empty">
              <p>Pose ta question sur les formations de l&apos;IIT et de l&apos;ISB.</p>
              <div className="chat-examples">
                {EXAMPLES.map((ex) => (
                  <button key={ex} type="button" onClick={() => void send(ex)} disabled={!token}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={`${m.sequence}-${i}`} className={`chat-bubble ${m.sender}`} dir="auto">
              {m.content}
              {m.sender === "user" && m.detected_language !== "unknown" && (
                <span className="chat-lang">{LANGUAGES[m.detected_language] ?? m.detected_language}</span>
              )}
            </div>
          ))}
          {sending && <div className="chat-bubble assistant chat-typing">L&apos;assistant réfléchit…</div>}
          <div ref={endRef} />
        </div>

        {error && <p className="chat-error" role="alert">{error}</p>}
        <form className="chat-form" onSubmit={onSubmit}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Écris ton message… (ex. 9adech el licence info ?)"
            maxLength={2000}
            dir="auto"
            disabled={!token}
            aria-label="Message"
          />
          <button className="primary-button" type="submit" disabled={!token || sending || !input.trim()}>
            Envoyer
          </button>
        </form>
        {meta && (
          <p className="preview-notice">
            Modèle : {meta.model} · {(meta.latency_ms / 1000).toFixed(1)} s
          </p>
        )}
      </section>

      <aside className="memory-card" aria-label="Mémoire de l'assistant">
        <span className="section-kicker">MÉMOIRE</span>
        <h3>Ce que l&apos;assistant retient</h3>
        {profile.length === 0 ? (
          <p className="memory-empty">Rien pour l&apos;instant. Parle de ton bac, ta moyenne ou tes centres d&apos;intérêt.</p>
        ) : (
          <dl>
            {profile.map(([key, value]) => (
              <div key={key}>
                <dt>{PROFILE_LABELS[key] ?? key}</dt>
                <dd>{Array.isArray(value) ? value.join(", ") : value}</dd>
              </div>
            ))}
          </dl>
        )}
        {memory && (
          <p className="memory-meta">
            {memory.turns} échange(s) · langue : {memory.language ? LANGUAGES[memory.language] ?? memory.language : "–"}
          </p>
        )}
      </aside>
    </div>
  );
}
