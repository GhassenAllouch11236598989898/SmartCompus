import type { Metadata } from "next";
import Link from "next/link";
import ChatPanel from "../../components/ChatPanel";

export const metadata: Metadata = {
  title: "Chatbot — SmartCampus AI",
  description: "Dialogue avec l'assistant d'orientation en français, tunisien ou Arabizi.",
};

export default function ChatPage() {
  return (
    <div className="site-shell">
      <header className="site-header">
        <Link className="brand" href="/">
          <span className="brand-icon" aria-hidden="true">S</span>
          <span>SmartCampus <b>AI</b></span>
        </Link>
        <nav aria-label="Navigation principale">
          <Link href="/">Accueil</Link>
          <Link href="/chat">Chatbot</Link>
        </nav>
        <span className="header-pill">SA-35 — Dialogue multi-tours</span>
      </header>
      <main className="section chat-section">
        <div className="section-heading">
          <span className="section-kicker">AGENT IA</span>
          <h2>Parle avec l&apos;assistant d&apos;orientation</h2>
          <p>Réponses générées par le LLM à partir du catalogue officiel, avec mémoire de la conversation.</p>
        </div>
        <ChatPanel />
      </main>
      <footer className="footer"><span>SmartCampus AI • IIT / ISB</span><span>SA-36 / SA-37 — LLM connecté au Backend</span></footer>
    </div>
  );
}
