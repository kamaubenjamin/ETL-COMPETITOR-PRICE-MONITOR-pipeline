import { Eye } from "lucide-react";

export function ReadOnlyNotice({ message = "This view is read-only." }: { message?: string }) {
  return <div className="read-only-notice"><Eye size={16} aria-hidden="true" /><span>{message}</span></div>;
}
