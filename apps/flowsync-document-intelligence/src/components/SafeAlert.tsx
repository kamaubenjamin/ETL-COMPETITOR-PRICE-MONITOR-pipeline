import type { ReactNode } from "react";

export function SafeAlert({ title, message, icon }: { title: string; message: string; icon?: ReactNode }) {
  return <aside className="safe-alert"><span className="safe-alert-icon">{icon}</span><div><strong>{title}</strong><p>{message}</p></div></aside>;
}
