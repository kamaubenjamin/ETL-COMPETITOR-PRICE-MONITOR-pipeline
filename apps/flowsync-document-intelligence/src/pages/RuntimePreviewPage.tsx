import { Server, ShieldCheck, Workflow } from "lucide-react";
import { StatusCard } from "../components/StatusCard";

export function RuntimePreviewPage() {
  return (
    <div className="page-stack">
      <section className="page-heading">
        <div><span className="eyebrow">Non-authoritative</span><h2>Runtime preview</h2><p>Safe display labels only.</p></div>
      </section>
      <section className="status-grid status-grid--three">
        <StatusCard label="API" value="Not connected" detail="No request has been made" icon={<Server size={18} />} />
        <StatusCard label="Runtime" value="API-owned" detail="UI cannot activate services" icon={<Workflow size={18} />} />
        <StatusCard label="Permissions" value="API-owned" detail="UI cannot grant access" tone="positive" icon={<ShieldCheck size={18} />} />
      </section>
    </div>
  );
}

