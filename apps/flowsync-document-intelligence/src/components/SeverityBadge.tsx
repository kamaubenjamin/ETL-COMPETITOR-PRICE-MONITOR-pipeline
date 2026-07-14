interface SeverityBadgeProps { severity: "warning" | "error"; }

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  return <span className={`severity-badge severity-badge--${severity}`}>{severity}</span>;
}
