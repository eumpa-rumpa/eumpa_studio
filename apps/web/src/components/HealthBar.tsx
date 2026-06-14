import { useHealth } from "../hooks/useHealth";

interface BadgeProps {
  label: string;
  status: string | undefined;
}

function Badge({ label, status }: BadgeProps) {
  const isOk = status === "ok";
  const className = isOk
    ? "health-bar__badge health-bar__badge--ok"
    : "health-bar__badge health-bar__badge--error";
  const indicator = isOk ? "✓" : "✗";
  return (
    <span className={className}>
      {label} {indicator}
    </span>
  );
}

export function HealthBar() {
  const { data, isLoading, error } = useHealth();

  if (isLoading) {
    return <span className="health-bar health-bar--checking">checking…</span>;
  }

  if (error) {
    return (
      <span className="health-bar health-bar--error">
        health error: {error}
      </span>
    );
  }

  return (
    <div className="health-bar">
      <Badge label="Backend" status={data?.backend} />
      <Badge label="Database" status={data?.database} />
      <Badge label="ComfyUI" status={data?.comfyui} />
      <Badge label="Codex CLI" status={data?.codex_cli} />
    </div>
  );
}
