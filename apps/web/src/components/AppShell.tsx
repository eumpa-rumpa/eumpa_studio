import { type ReactNode } from "react";
import { HealthBar } from "./HealthBar";

interface AppShellProps {
  children?: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <h1 className="app-shell__title">eumpa studio</h1>
        <HealthBar />
      </header>
      <main className="app-shell__main">{children}</main>
    </div>
  );
}
