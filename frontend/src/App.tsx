import { useEffect, useState } from "react";

type BackendState = "checking" | "ready" | "unavailable";

export function App() {
  const [backendState, setBackendState] = useState<BackendState>("checking");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((response) => {
        if (!response.ok) throw new Error("Backend health check failed");
        return response.json();
      })
      .then((health: { status?: string }) => {
        setBackendState(health.status === "ok" ? "ready" : "unavailable");
      })
      .catch(() => setBackendState("unavailable"));
  }, []);

  const statusLabel = {
    checking: "Checking backend…",
    ready: "Backend ready",
    unavailable: "Backend unavailable",
  }[backendState];

  return (
    <main>
      <p className="eyebrow">Synthetic utility operations demo</p>
      <h1>GRIDOPS AGENT</h1>
      <p className={`status status--${backendState}`}>{statusLabel}</p>
      <p className="note">Infrastructure foundation only. Incident workflows come later.</p>
    </main>
  );
}
