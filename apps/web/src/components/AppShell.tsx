import { useEffect, useState, type ReactNode } from "react";
import { fetchHealth } from "../api/client";
import type { HealthResponse } from "../api/types";

interface AppShellProps {
  children?: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown error");
      });
  }, []);

  const healthLabel = error
    ? `error: ${error}`
    : health
      ? health.status
      : "checking…";

  const healthClass = error
    ? "app-shell__health app-shell__health--error"
    : health?.status === "ok"
      ? "app-shell__health app-shell__health--ok"
      : "app-shell__health";

  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <h1 className="app-shell__title">eumpa studio</h1>
        <span className={healthClass}>{healthLabel}</span>
      </header>
      <main className="app-shell__main">{children}</main>
    </div>
  );
}
