import type { ReactNode } from "react";

export type StatusTone = "neutral" | "positive" | "warning" | "critical";

interface StatusCardProps {
  label: string;
  value: string;
  detail: string;
  tone?: StatusTone;
  icon?: ReactNode;
}

export function StatusCard({ label, value, detail, tone = "neutral", icon }: StatusCardProps) {
  return (
    <article className={`status-card status-card--${tone}`}>
      <div className="status-card-heading">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

