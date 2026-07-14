import type { DocumentDetailViewModel } from "../types/viewModels";
import { StatusChip } from "./StatusChip";

interface DocumentMetadataPanelProps {
  document: DocumentDetailViewModel;
}

export function DocumentMetadataPanel({ document }: DocumentMetadataPanelProps) {
  const fields = [
    ["Document ID", document.id],
    ["Document type", document.type],
    ["Current stage", document.currentStage],
    ["Confidence", document.confidence],
    ["Received", document.receivedAt],
    ["Updated", document.updatedAt],
    ["Source", document.source],
  ] as const;

  return (
    <section className="metadata-panel" aria-labelledby="metadata-heading">
      <div className="metadata-panel-heading">
        <div>
          <span className="eyebrow">Safe metadata</span>
          <h3 id="metadata-heading">{document.filename}</h3>
        </div>
        <StatusChip status={document.status} label={document.statusLabel} />
      </div>
      <dl className="metadata-grid">
        {fields.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
        ))}
      </dl>
    </section>
  );
}

