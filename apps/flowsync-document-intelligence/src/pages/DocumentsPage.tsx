import { CircleAlert, CircleCheck, FileInput, ScanLine } from "lucide-react";
import { EmptyState } from "../components/EmptyState";
import { StatusCard } from "../components/StatusCard";

export function DocumentsPage() {
  return (
    <div className="page-stack">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Operational overview</span>
          <h2>Document workload</h2>
          <p>Secure read-first workspace for document processing status.</p>
        </div>
        <span className="phase-label">Phase 1 shell</span>
      </section>

      <section className="status-grid" aria-label="Document status summary">
        <StatusCard label="Received" value="--" detail="Awaiting API connection" icon={<FileInput size={18} />} />
        <StatusCard label="Processing" value="--" detail="Awaiting API connection" tone="warning" icon={<ScanLine size={18} />} />
        <StatusCard label="Review required" value="--" detail="Awaiting API connection" tone="critical" icon={<CircleAlert size={18} />} />
        <StatusCard label="Export ready" value="--" detail="Awaiting API connection" tone="positive" icon={<CircleCheck size={18} />} />
      </section>

      <section className="content-section">
        <div className="section-heading">
          <div><span className="eyebrow">Documents</span><h2>Inbox</h2></div>
          <span className="read-only-label">Read-only</span>
        </div>
        <EmptyState title="Document data is not connected" message="The API client contract is ready for Phase 2 integration." />
      </section>
    </div>
  );
}

