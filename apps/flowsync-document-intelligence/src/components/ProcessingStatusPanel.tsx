import { Activity, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { createApiClient } from "../api/client";
import { getDocumentProcessingStatus } from "../api/uploads";
import { isRequestFailure, toRequestFailure, type RequestState } from "../state/requestState";
import { statusLabel } from "../state/uploadViewModels";
import type { UploadProgressSummary } from "../types/upload";
import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { SafeErrorState } from "./SafeErrorState";
import { StatusChip } from "./StatusChip";

export function ProcessingStatusPanel({ documentId }: { documentId: string }) {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<UploadProgressSummary>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    getDocumentProcessingStatus(createApiClient(), documentId)
      .then((envelope) => { if (active) setState(envelope.data ? { status: "success", data: envelope.data } : { status: "empty" }); })
      .catch((error) => { if (active) setState(toRequestFailure(error)); });
    return () => { active = false; };
  }, [documentId, reloadKey]);

  return (
    <section className="processing-status-panel" aria-labelledby="processing-status-heading">
      <div className="section-heading upload-section-heading">
        <div><span className="eyebrow">Upload processing</span><h2 id="processing-status-heading">Current processing status</h2></div>
        <button className="secondary-button compact-button" type="button" onClick={() => setReloadKey((value) => value + 1)}><RefreshCw size={15} aria-hidden="true" /> Refresh</button>
      </div>
      {state.status === "loading" ? <LoadingState label="Loading processing status" /> : null}
      {state.status === "empty" || state.status === "idle" ? <EmptyState title="Processing status unavailable" message="No upload-linked processing status was supplied." /> : null}
      {isRequestFailure(state) ? <div className="embedded-safe-state"><SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} /></div> : null}
      {state.status === "success" ? (
        <div className="document-processing-summary">
          <span className="document-processing-icon"><Activity size={20} aria-hidden="true" /></span>
          <div><span>Current stage</span><strong>{state.data.stageLabel}</strong><small>Updated {state.data.updatedAt}</small></div>
          <StatusChip status={state.data.status} label={statusLabel(state.data.status)} />
        </div>
      ) : null}
    </section>
  );
}
