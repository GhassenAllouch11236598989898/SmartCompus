import BackendStatus from "../components/BackendStatus";

const journeys = [
  {
    number: "01",
    title: "Découvrir les formations",
    text: "Explorer les parcours proposés par l’IIT et l’ISB.",
    tag: "À connecter aux données officielles",
  },
  {
    number: "02",
    title: "Parler avec l’agent IA",
    text: "Poser des questions en français, tunisien ou Arabizi.",
    tag: "Chatbot à développer",
  },
  {
    number: "03",
    title: "Suivre sa candidature",
    text: "Préinscription, QCM, rendez-vous et suivi du dossier.",
    tag: "Espace candidat à développer",
  },
];

export default function Home() {
  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">S</span>
          <span>SmartCampus <b>AI</b></span>
        </div>
        <nav aria-label="Navigation principale">
          <a href="#parcours">Parcours</a>
          <a href="#fonctionnement">Fonctionnement</a>
          <a href="#connexion">Connexion API</a>
        </nav>
        <span className="header-pill">Projet universitaire</span>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <span className="eyebrow"><span className="eyebrow-dot" /> Orientation universitaire assistée par IA</span>
            <h1 id="hero-title">Choisir sa formation devient <em>plus simple.</em></h1>
            <p>SmartCampus AI accompagne les futurs étudiants pour découvrir les formations de l’IIT et de l’ISB et préparer leur candidature.</p>
            <div className="hero-actions">
              <a className="primary-button" href="#parcours">Découvrir le projet <span aria-hidden="true">→</span></a>
              <a className="secondary-button" href="#connexion">Vérifier le Backend</a>
            </div>
          </div>
          <div className="preview-card" aria-label="Exemple d'une future conversation">
            <div className="preview-top"><span className="preview-avatar">AI</span><div><b>Assistant SmartCampus</b><small>Présentation de l'interface</small></div><span className="preview-tag">Aperçu</span></div>
            <div className="preview-message user">Je cherche une formation en informatique.</div>
            <div className="preview-message assistant">L’agent pourra te poser des questions et t’aider à comparer les parcours.</div>
            <div className="preview-input">Chatbot bientôt disponible <span>↗</span></div>
            <p className="preview-notice">Démonstration visuelle uniquement : aucune réponse IA réelle n'est générée ici.</p>
          </div>
        </section>

        <section id="parcours" className="section section-features" aria-labelledby="parcours-title">
          <div className="section-heading"><span className="section-kicker">LE PROJET</span><h2 id="parcours-title">Un seul espace pour avancer</h2><p>Les fonctions prévues dans le cahier des charges.</p></div>
          <div className="feature-grid">
            {journeys.map((item) => (
              <article className="feature-card" key={item.number}>
                <span className="feature-number">{item.number}</span>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
                <span className="feature-tag">{item.tag}</span>
              </article>
            ))}
          </div>
        </section>

        <section id="fonctionnement" className="section workflow" aria-labelledby="flow-title">
          <div><span className="section-kicker">ARCHITECTURE</span><h2 id="flow-title">Comment ça fonctionne ?</h2><p>Le Frontend communique avec le Backend FastAPI. Les agents IA et les autres services seront intégrés ensuite.</p></div>
          <div className="flow-line" aria-label="Utilisateurs vers Frontend vers Backend vers services futurs">
            <span>Utilisateur</span><b>→</b><span>Next.js</span><b>→</b><span>FastAPI</span><b>→</b><span className="future">IA + Données (à venir)</span>
          </div>
        </section>

        <section id="connexion" className="section connection" aria-labelledby="connexion-title">
          <div className="section-heading"><span className="section-kicker">TEST TECHNIQUE</span><h2 id="connexion-title">Connexion au Backend</h2><p>La vérification utilise l'API <code>GET /api/v1/health</code>.</p></div>
          <BackendStatus />
        </section>
      </main>
      <footer className="footer"><span>SmartCampus AI • IIT / ISB</span><span>SA-8 — Initialisation Frontend</span></footer>
    </div>
  );
}
