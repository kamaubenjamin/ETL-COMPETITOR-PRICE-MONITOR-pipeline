import { AlertTriangle, Server, ShieldCheck, Workflow } from "lucide-react";
import { ReadOnlyNotice } from "../components/ReadOnlyNotice";
import { SafeAlert } from "../components/SafeAlert";
import { StatusCard } from "../components/StatusCard";

export function RuntimePreviewPage() {
  return (
    <div className="page-stack">
      <section className="page-heading">
        <div><span className="eyebrow">Non-authoritative</span><h2>Runtime preview</h2><p>Display-only guidance; runtime and access decisions remain API-owned.</p></div>
        <ReadOnlyNotice message="Local preview cannot activate or reconfigure platform services." />
      </section>
      <section className="status-grid status-grid--three">
        <StatusCard label="API" value="Not connected" detail="No request has been made" icon={<Server size={18} />} />
        <StatusCard label="Runtime" value="API-owned" detail="UI cannot activate services" icon={<Workflow size={18} />} />
        <StatusCard label="Permissions" value="API-owned" detail="UI cannot grant access" tone="positive" icon={<ShieldCheck size={18} />} />
      </section>
      <section className="safe-alert-grid safe-alert-grid--two" aria-label="Runtime state guidance">
        <SafeAlert icon={<Server size={17} />} title="API unavailable" message="The UI shows a fixed unavailable state and does not substitute local records." />
        <SafeAlert icon={<Workflow size={17} />} title="Runtime unavailable" message="Runtime status comes from the API; this display cannot select a backend." />
        <SafeAlert icon={<ShieldCheck size={17} />} title="Access mismatch" message="Environment access configuration is resolved outside the frontend." />
        <SafeAlert icon={<AlertTriangle size={17} />} title="Malformed response" message="Unvalidated response data is withheld and replaced with a fixed safe message." />
      </section>
    </div>
  );
}
