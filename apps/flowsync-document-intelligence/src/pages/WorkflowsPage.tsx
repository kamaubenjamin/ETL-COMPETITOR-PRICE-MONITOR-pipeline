import { Activity, CircleCheck, CircleX, Workflow } from "lucide-react";
import { useEffect, useState } from "react";
import { createApiClient } from "../api/client";
import { toSafeClientError } from "../api/errors";
import { listWorkflowRuns } from "../api/workflows";
import { DataTable, type DataTableColumn } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { ReadOnlyNotice } from "../components/ReadOnlyNotice";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusCard } from "../components/StatusCard";
import { StatusChip } from "../components/StatusChip";
import { TimelineList } from "../components/TimelineList";
import { displayLabel, formatDateTime } from "../state/documentViewModels";
import { formatDuration, workflowTimeline } from "../state/operationalViewModels";
import type { RequestState } from "../state/requestState";
import type { WorkflowRunSummary } from "../types/workflow";

const COLUMNS: readonly DataTableColumn<WorkflowRunSummary>[] = [
  { key: "run", header: "Run", render: (row) => row.run_id },
  { key: "workflow", header: "Workflow", render: (row) => displayLabel(row.workflow_name) },
  { key: "type", header: "Type", render: (row) => row.workflow_type ? displayLabel(row.workflow_type) : "Not available" },
  { key: "status", header: "Status", render: (row) => <StatusChip status={row.status} /> },
  { key: "document", header: "Document", render: (row) => row.document_id ?? "Not available" },
  { key: "started", header: "Started", render: (row) => formatDateTime(row.started_at) },
  { key: "ended", header: "Ended", render: (row) => formatDateTime(row.ended_at) },
  { key: "duration", header: "Duration", render: (row) => formatDuration(row.duration_ms) },
];

export function WorkflowsPage() {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<WorkflowRunSummary[]>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    listWorkflowRuns(createApiClient()).then((result) => {
      const data = result.data ?? [];
      if (active) setState(data.length ? { status: "success", data } : { status: "empty" });
    }).catch((error) => { if (active) setState({ status: "error", error: toSafeClientError(error) }); });
    return () => { active = false; };
  }, [reloadKey]);
  if (state.status === "loading") return <LoadingState label="Loading workflow activity" />;
  if (state.status === "error") return <SafeErrorState error={state.error} onRetry={() => setReloadKey((v) => v + 1)} />;
  if (state.status !== "success") return <EmptyState title="No workflow runs" message="The API returned no workflow activity for this view." />;
  const running = state.data.filter((item) => item.status === "running" || item.status === "queued").length;
  const succeeded = state.data.filter((item) => item.status === "succeeded").length;
  const failed = state.data.filter((item) => item.status === "failed").length;
  return <div className="page-stack">
    <section className="page-heading"><div><span className="eyebrow">Runtime activity</span><h2>Workflow runs</h2><p>Safe execution summaries from the read-only API boundary.</p></div><ReadOnlyNotice message="Workflow execution and retries are not available." /></section>
    <section className="status-grid"><StatusCard label="Current runs" value={String(state.data.length)} detail="Current API result" icon={<Workflow size={18} />} /><StatusCard label="Active" value={String(running)} detail="Queued or running" tone={running ? "warning" : "neutral"} icon={<Activity size={18} />} /><StatusCard label="Succeeded" value={String(succeeded)} detail="Completed runs" tone="positive" icon={<CircleCheck size={18} />} /><StatusCard label="Failed" value={String(failed)} detail="Requires investigation" tone={failed ? "critical" : "positive"} icon={<CircleX size={18} />} /></section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Run register</span><h2>Workflow history</h2></div></div><DataTable caption="Workflow runs" columns={COLUMNS} rows={state.data} rowKey={(row) => row.run_id} /></section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Timeline</span><h2>Recent activity</h2></div></div><TimelineList items={workflowTimeline(state.data)} /></section>
  </div>;
}
