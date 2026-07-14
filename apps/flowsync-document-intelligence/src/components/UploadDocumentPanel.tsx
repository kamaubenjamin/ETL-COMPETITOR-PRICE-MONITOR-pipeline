import { FileCheck2, FileUp, ShieldCheck } from "lucide-react";
import { useState, type ChangeEvent, type FormEvent } from "react";
import { createApiClient } from "../api/client";
import { validateUploadMetadataPreview } from "../api/uploads";
import { toRequestFailure, type RequestFailureState } from "../state/requestState";
import { toSelectedUploadMetadata, toUploadPreviewRequest, type SelectedUploadMetadata } from "../state/uploadViewModels";
import type { UploadValidationPreviewResult } from "../types/upload";
import { SafeErrorState } from "./SafeErrorState";
import { UploadValidationSummary } from "./UploadValidationSummary";

export function UploadDocumentPanel() {
  const [selection, setSelection] = useState<SelectedUploadMetadata | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<UploadValidationPreviewResult | null>(null);
  const [failure, setFailure] = useState<RequestFailureState | null>(null);

  const selectFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.item(0);
    setSelection(file ? toSelectedUploadMetadata(file) : null);
    setResult(null);
    setFailure(null);
  };

  const submitPreview = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selection || submitting) return;
    setSubmitting(true);
    setResult(null);
    setFailure(null);
    try {
      const preview = await validateUploadMetadataPreview(createApiClient(), toUploadPreviewRequest(selection));
      setResult(preview);
    } catch (error) {
      setFailure(toRequestFailure(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="upload-card" aria-labelledby="upload-preview-heading">
      <div className="upload-card-heading">
        <div className="upload-heading-icon"><FileUp size={22} aria-hidden="true" /></div>
        <div>
          <span className="eyebrow">Guarded preview</span>
          <h2 id="upload-preview-heading">Upload validation preview</h2>
          <p>The selected file will not leave this browser in the current release.</p>
        </div>
      </div>

      <form className="upload-preview-form" onSubmit={submitPreview}>
        <label className="file-picker" htmlFor="upload-file-picker">
          <FileCheck2 size={28} aria-hidden="true" />
          <strong>{selection ? "Choose a different document" : "Choose a document"}</strong>
          <span>PDF, CSV, XLSX, TXT, or EML metadata can be validated.</span>
          <input
            id="upload-file-picker"
            type="file"
            accept=".pdf,.csv,.xlsx,.txt,.eml"
            onChange={selectFile}
          />
        </label>

        {selection ? (
          <dl className="selected-file-summary" aria-label="Selected file metadata">
            <div><dt>Filename</dt><dd>{selection.filename}</dd></div>
            <div><dt>Type</dt><dd>{selection.fileType.toUpperCase()}</dd></div>
            <div><dt>Size</dt><dd>{selection.sizeLabel}</dd></div>
            <div><dt>Browser check</dt><dd>{selection.browserHint === "supported" ? "Supported type hint" : selection.browserHint === "empty" ? "Empty file" : "Unsupported type hint"}</dd></div>
          </dl>
        ) : null}

        <div className="upload-action-row">
          <button className="primary-button" type="submit" disabled={!selection || submitting}>
            <ShieldCheck size={17} aria-hidden="true" />
            {submitting ? "Validating metadata…" : "Validate upload"}
          </button>
          <p>Processing will become available after the staging boundary is activated.</p>
        </div>
      </form>

      {result ? <UploadValidationSummary result={result} /> : null}
      {failure ? <SafeErrorState error={failure.error} /> : null}
    </section>
  );
}

