import { ShieldCheck } from "lucide-react";

export function AccessScopeNotice() {
  return (
    <aside className="access-scope-notice" aria-label="Access scope information">
      <ShieldCheck size={17} aria-hidden="true" />
      <div>
        <strong>API-enforced visibility</strong>
        <span>Showing records available to your current access scope. Some records may be hidden by your organization's permissions.</span>
      </div>
    </aside>
  );
}
