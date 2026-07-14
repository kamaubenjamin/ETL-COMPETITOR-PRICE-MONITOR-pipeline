import { AlertCircle, CheckCircle2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { createApiClient } from "../api/client";
import { getUploadProgress, getUploadTimeline } from "../api/uploads";
import { isRequestFailure, malformedRequestState, toRequestFailure, type RequestState } from "../state/requestState";
import { formatUploadTime, statusLabel } from "../state/uploadViewModels";
import type { UploadProgressSummary, UploadTimeline } from "../types/upload";
import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { SafeErrorState } from "./SafeErrorState";
import { StatusChip } from "./StatusChip";

interface TimelineData { progress: UploadProgressSummary; timeline: UploadTimeline }
interface UploadProgressTimelineProps { uploadId: string | null }

export function UploadProgressTimeline({ uploadId }: UploadProgressTimelineProps) {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<TimelineData>>({ status: "idle" });

  useEffect(() => {
    let active = true;
    if (!uploadId) { setState({ status: "idle" }); return () => { active = false; }; }
    setState({ status: "loading" });
    const client = createApiClient();
    Promise.all([getUploadProgress(client, uploadId), getUploadTimeline(client, uploadId)])
      .then(([progress, timeline]) => {
        if (!active) return;
        if (!progress.data || !timeline.data || progress.data.uploadId !== timeline.data.uploadId) {
          setState(malformedRequestState(progress.request_id));
          return;
        }
        setState({ status: "success", data: { progress: progress.data, timeline: timeline.data } });
      })
      .catch((error) => { if (active) setState(toRequestFailure(error)); });
    return () => { active = false; };
  }, [uploadId, reloadKey]);

  return (
    <section className="content-section" aria-labelledby="upload-timeline-heading">
      <div className="section-heading upload-section-heading">
        <div><span className="eyebrow">Read-only status</span><h2 id="upload-timeline-heading">Processing timeline</h2></div>
        {uploadId ? <button className="secondary-button compact-button" type="button" onClick={() => setReloadKey((value) => value + 1)}><RefreshCw size={15} aria-hidden="true" /> Refresh</button> : null}
      </div>
      {!uploadId || state.status === "idle" ? <EmptyState title="Select an upload" message="Choose an API record to view its supplied progress and timeline." /> : null}
      {state.status === "loading" ? <LoadingState label="Loading upload progress" /> : null}
      {isRequestFailure(state) ? <SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
      {state.status === "success" ? <TimelineContent data={state.data} /> : null}
    </section>
  );
}

function TimelineContent({ data }: { data: TimelineData }) {
  const { progress, timeline } = data;
  return (
    <div className="upload-progress-stack">
      <div className="progress-summary-card">
        <div><span>Current stage</span><strong>{progress.stageLabel}</strong></div>
        <StatusChip status={progress.status} label={statusLabel(progress.status)} />
        {progress.progressPercent !== null ? (
          <div className="progress-meter-wrap">
            <div className="progress-meter-label"><span>{progress.progressApproximate ? "Approximate progress" : "Progress"}</span><strong>{progress.progressPercent}%</strong></div>
            <div className="progress-meter" role="progressbar" aria-label={progress.progressApproximate ? "Approximate processing progress" : "Processing progress"} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.progressPercent}>
              <span style={{ width: `${progress.progressPercent}%` }} />
            </div>
          </div>
        ) : <p>Progress percentage is unavailable because the API did not supply sufficient stage facts.</p>}
        {progress.failure ? <div className="progress-failure"><AlertCircle size={17} aria-hidden="true" /><div><strong>{progress.failure.summary}</strong><span>Code: {progress.failure.code}</span></div></div> : null}
      </div>
      {timeline.events.length === 0 ? (
        <EmptyState title="No timeline events" message="No completed processing events were supplied by the API." />
      ) : (
        <ol className="processing-timeline upload-processing-timeline">
          {timeline.events.map((event, index) => (
            <li key={`${event.stage.code}-${event.occurredAt}-${index}`}>
              <div className="timeline-marker"><CheckCircle2 size={15} aria-hidden="true" /></div>
              <div><strong>{event.stage.label}</strong><span>{event.summary} · {formatUploadTime(event.occurredAt)}</span></div>
              <StatusChip status={event.status} label={statusLabel(event.status)} />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

