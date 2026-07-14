import { ArrowLeft, ClipboardList, FilePenLine, RefreshCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createApiClient } from "../api/client";
import { getReviewCase, listCorrectionHistory, listReprocessPlans } from "../api/reviews";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { PriorityBadge } from "../components/PriorityBadge";
import { ReadOnlyNotice } from "../components/ReadOnlyNotice";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusCard } from "../components/StatusCard";
import { StatusChip } from "../components/StatusChip";
import { TimelineList } from "../components/TimelineList";
import { displayLabel, formatDateTime } from "../state/documentViewModels";
import { correctionTimeline, reprocessTimeline } from "../state/operationalViewModels";
import { isRequestFailure, malformedRequestState, notFoundRequestState, toRequestFailure, type RequestState } from "../state/requestState";
import type { CorrectionSummary, ReprocessPlanSummary, ReviewCaseSummary } from "../types/review";

interface ReviewDetailData { reviewCase: ReviewCaseSummary; corrections: CorrectionSummary[]; plans: ReprocessPlanSummary[]; }

export function ReviewCaseDetailPage() {
  const { reviewCaseId } = useParams<{ reviewCaseId: string }>();
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<ReviewDetailData>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    if (!reviewCaseId) { setState(notFoundRequestState()); return () => { active = false; }; }
    const client = createApiClient();
    Promise.all([getReviewCase(client, reviewCaseId), listCorrectionHistory(client, reviewCaseId), listReprocessPlans(client)])
      .then(([reviewCase, corrections, plans]) => {
        if (!active) return;
        if (!reviewCase.data || !corrections.data || !plans.data) setState(malformedRequestState(reviewCase.request_id));
        else setState({ status: "success", data: { reviewCase: reviewCase.data, corrections: corrections.data, plans: plans.data.filter((plan) => plan.review_case_id === reviewCaseId) } });
      }).catch((error) => { if (active) setState(toRequestFailure(error)); });
    return () => { active = false; };
  }, [reviewCaseId, reloadKey]);
  if (state.status === "loading") return <LoadingState label="Loading review case" />;
  if (isRequestFailure(state)) return <SafeErrorState error={state.error} onRetry={() => setReloadKey((v) => v + 1)} />;
  if (state.status !== "success") return <EmptyState title="Review case unavailable" message="No safe case summary was returned." />;
  const item = state.data.reviewCase;
  return <div className="page-stack">
    <section className="page-heading"><div><Link className="back-link" to="/review"><ArrowLeft size={16} /> Review queue</Link><span className="eyebrow">Review case</span><h2>{item.review_case_id}</h2><p>Created {formatDateTime(item.created_at)}</p></div><ReadOnlyNotice message="Case decisions and corrections cannot be submitted here." /></section>
    <section className="status-grid">
      <StatusCard label="Status" value={displayLabel(item.status)} detail="Current case state" icon={<ClipboardList size={18} />} />
      <StatusCard label="Priority" value={displayLabel(item.priority)} detail="Workload priority" tone={item.priority === "urgent" || item.priority === "high" ? "critical" : "neutral"} />
      <StatusCard label="Corrections" value={String(item.correction_count)} detail="Summary records only" icon={<FilePenLine size={18} />} />
      <StatusCard label="Reprocess state" value={displayLabel(item.reprocess_state)} detail="Planning status" icon={<RefreshCcw size={18} />} />
    </section>
    <section className="metadata-panel"><div className="metadata-panel-heading"><div><span className="eyebrow">Case metadata</span><h3>{item.review_case_id}</h3></div><StatusChip status={item.status} /></div><dl className="metadata-grid"><div><dt>Document reference</dt><dd><Link className="back-link" to={`/documents/${encodeURIComponent(item.document_id)}`}>{item.document_id}</Link></dd></div><div><dt>Reason</dt><dd>{displayLabel(item.reason_code)}</dd></div><div><dt>Assigned reviewer</dt><dd>{item.assigned_reviewer ?? "Unassigned"}</dd></div><div><dt>Priority</dt><dd><PriorityBadge priority={item.priority} /></dd></div><div><dt>Decision</dt><dd>{item.decision_code ? displayLabel(item.decision_code) : "Not recorded"}</dd></div><div><dt>Updated</dt><dd>{formatDateTime(item.updated_at)}</dd></div></dl></section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">History</span><h2>Correction summaries</h2></div></div>{state.data.corrections.length ? <TimelineList items={correctionTimeline(state.data.corrections)} /> : <EmptyState title="No correction summaries" message="No protected values are displayed in this view." />}</section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Planning</span><h2>Reprocess plans</h2></div></div>{state.data.plans.length ? <TimelineList items={reprocessTimeline(state.data.plans)} /> : <EmptyState title="No reprocess plan" message="No read-only reprocess plan is associated with this case." />}</section>
  </div>;
}
