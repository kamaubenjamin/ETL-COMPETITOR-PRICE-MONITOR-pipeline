import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { RecentUploadsPanel } from "../components/RecentUploadsPanel";
import { UploadDocumentPanel } from "../components/UploadDocumentPanel";
import { UploadProgressTimeline } from "../components/UploadProgressTimeline";
import type { RecentUploadViewModel } from "../state/uploadViewModels";

export function UploadsPage() {
  const [selected, setSelected] = useState<RecentUploadViewModel | null>(null);
  return (
    <div className="page-stack uploads-page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Controlled document intake</span>
          <h2>Uploads</h2>
          <p>Validate browser-local file metadata and inspect API-owned processing status.</p>
        </div>
        <div className="read-only-notice"><ShieldCheck size={16} aria-hidden="true" /> API authority preserved · staging disabled</div>
      </section>

      <div className="upload-capability-banner" role="note">
        <strong>File staging is not enabled yet</strong>
        <span>This release validates metadata only. It does not transfer, stage, or process the selected document.</span>
      </div>

      <UploadDocumentPanel />

      <div className="upload-read-grid">
        <RecentUploadsPanel selectedUploadId={selected?.id ?? null} onSelect={setSelected} />
        <UploadProgressTimeline uploadId={selected?.id ?? null} />
      </div>
    </div>
  );
}

