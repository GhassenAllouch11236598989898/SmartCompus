"use client";

import { useCallback, useEffect, useState } from "react";

type HealthResponse = { status: string; service: string };
type ConnectionStatus = "loading" | "online" | "offline";

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function BackendStatus() {
  const [status, setStatus] = useState<ConnectionStatus>("loading");

  const checkConnection = useCallback(async () => {
    setStatus("loading");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    try {
      const res = await fetch(`${API_URL}/api/v1/health`, {
        signal: controller.signal,
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: HealthResponse = await res.json();
      setStatus(data.status === "ok" ? "online" : "offline");
    } catch {
      setStatus("offline");
    } finally {
      clearTimeout(timeout);
    }
  }, []);

  useEffect(() => { void checkConnection(); }, [checkConnection]);

  const label = status === "online" ? "API connectée" : status === "loading" ? "Vérification…" : "API non connectée";
  const description = status === "online"
    ? "Le Frontend communique avec FastAPI."
    : status === "loading"
    ? "Recherche du serveur FastAPI local."
    : "Démarre FastAPI sur le port 8000, puis réessaie.";

  return (
    <div className="status-card" aria-live="polite">
      <div className="status-copy">
        <span className={`status-dot ${status}`} aria-hidden="true" />
        <div>
          <strong>{label}</strong>
          <p>{description}</p>
        </div>
      </div>
      <button className="status-button" type="button" onClick={() => void checkConnection()} disabled={status === "loading"}>
        Actualiser
      </button>
    </div>
  );
}
