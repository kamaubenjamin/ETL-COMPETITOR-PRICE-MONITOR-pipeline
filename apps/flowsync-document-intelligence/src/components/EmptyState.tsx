import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title: string;
  message: string;
}

export function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <section className="empty-state" aria-live="polite">
      <Inbox size={24} aria-hidden="true" />
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

