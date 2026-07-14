import type { ReactNode } from "react";

interface DocumentSectionCardProps {
  title: string;
  value: string;
  detail: string;
  icon: ReactNode;
}

export function DocumentSectionCard({ title, value, detail, icon }: DocumentSectionCardProps) {
  return (
    <article className="document-section-card">
      <div className="document-section-icon" aria-hidden="true">{icon}</div>
      <div><span>{title}</span><strong>{value}</strong><p>{detail}</p></div>
    </article>
  );
}

