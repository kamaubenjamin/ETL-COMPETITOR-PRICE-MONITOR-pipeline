import { AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react";
import type { UploadValidationPreviewResult } from "../types/upload";

interface UploadValidationSummaryProps {
  result: UploadValidationPreviewResult;
}

export function UploadValidationSummary({ result }: UploadValidationSummaryProps) {
  const governed = result.outcome === "staging_unavailable";
  const Icon = governed ? CheckCircle2 : AlertTriangle;
  return (
    <div className={`upload-validation-result upload-validation-result--${governed ? "governed" : "invalid"}`} role="status" aria-live="polite">
      <Icon size={20} aria-hidden="true" />
      <div>
        <strong>{result.title}</strong>
        <p>{result.message}</p>
        {result.outcome === "invalid" && (result.issueCode || result.field) ? (
          <span>{result.field ? `Field: ${result.field}. ` : ""}{result.issueCode ? `Issue: ${result.issueCode}.` : ""}</span>
        ) : null}
        {governed ? <span><ShieldCheck size={14} aria-hidden="true" /> No staging or processing occurred.</span> : null}
      </div>
    </div>
  );
}

