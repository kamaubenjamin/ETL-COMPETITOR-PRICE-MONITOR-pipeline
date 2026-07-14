import { Clock3, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { createApiClient } from "../api/client";
import { listUploads } from "../api/uploads";
import { isRequestFailure, toRequestFailure, type RequestState } from "../state/requestState";
import { toRecentUploadViewModel, type RecentUploadViewModel } from "../state/uploadViewModels";
import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { SafeErrorState } from "./SafeErrorState";
import { StatusChip } from "./StatusChip";

interface RecentUploadsPanelProps {
  selectedUploadId: string | null;
  onSelect: (upload: RecentUploadViewModel) => void;
}

export function RecentUploadsPanel({ selectedUploadId, onSelect }: RecentUploadsPanelProps) {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<RecentUploadViewModel[]>>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    listUploads(createApiClient())
      .then((envelope) => {
        if (!active) return;
        const rows = (envelope.data ?? []).map(toRecentUploadViewModel);
        setState(rows.length ? { status: "success", data: rows } : { status: "empty" });
      })
      .catch((error) => { if (active) setState(toRequestFailure(error)); });
    return () => { active = false; };
  }, [reloadKey]);

  return (
    <section className="content-section" aria-labelledby="recent-uploads-heading">
      <div className="section-heading upload-section-heading">
        <div><span className="eyebrow">API records</span><h2 id="recent-uploads-heading">Recent uploads</h2></div>
        <button className="secondary-button compact-button" type="button" onClick={() => setReloadKey((value) => value + 1)}>
          <RefreshCw size={15} aria-hidden="true" /> Refresh
        </button>
      </div>
      {state.status === "loading" ? <LoadingState label="Loading recent uploads" /> : null}
      {state.status === "empty" || state.status === "idle" ? (
        <EmptyState title="No recent uploads" message="The API returned no upload records for the current access scope." />
      ) : null}
      {isRequestFailure(state) ? <SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
      {state.status === "success" ? (
        <div className="recent-upload-list">
          {state.data.map((upload) => (
            <button
              className={`recent-upload-row ${selectedUploadId === upload.id ? "recent-upload-row--selected" : ""}`}
              type="button"
              key={upload.id}
              onClick={() => onSelect(upload)}
              aria-pressed={selectedUploadId === upload.id}
            >
              <span className="recent-upload-icon"><Clock3 size={17} aria-hidden="true" /></span>
              <span className="recent-upload-name"><strong>{upload.filename}</strong><small>{upload.typeAndSize} · {upload.receivedAt}</small></span>
              <StatusChip status={upload.status} label={upload.statusLabel} />
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

