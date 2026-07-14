export const UPLOAD_STATUSES = [
  "received", "validation_failed", "validated", "staged", "ingestion_requested",
  "processing_started", "completed", "failed", "duplicate_prevented",
  "deferred_staging_required", "unsupported_activation", "document_state_recorded",
] as const;

export type UploadProcessingStatus = (typeof UPLOAD_STATUSES)[number];

const UPLOAD_STAGE_CODES = [
  "received", "validated", "staged", "document_state_recorded", "ingestion_requested",
  "processing_started", "ingested", "parsed", "extracted", "transformed",
  "validated_output", "matched", "review_required", "completed", "failed",
] as const;

export interface UploadFailure {
  code: string;
  summary: string;
}

export interface UploadProgressSummary {
  uploadId: string;
  documentId: string | null;
  status: UploadProcessingStatus;
  currentStage: string;
  stageLabel: string;
  stageSequence: number;
  startedAt: string;
  updatedAt: string;
  completedAt: string | null;
  progressPercent: number | null;
  progressApproximate: boolean;
  failure: UploadFailure | null;
  actorLabel: string | null;
  sourceLabel: string | null;
}

export interface UploadProgressEvent {
  stage: { code: string; label: string; sequence: number; completed: boolean; occurredAt: string | null };
  status: UploadProcessingStatus;
  occurredAt: string;
  summary: string;
}

export interface UploadTimeline {
  uploadId: string;
  events: UploadProgressEvent[];
}

export interface UploadSummary {
  uploadId: string;
  documentId: string | null;
  filename: string;
  fileType: string;
  fileSizeBytes: number;
  source: string;
  status: UploadProcessingStatus;
  receivedAt: string;
  processing: UploadProgressSummary | null;
}

export interface UploadMetadataPreviewRequest {
  filename: string;
  file_size_bytes: number;
  file_type: string;
  declared_content_type?: string;
  source: "flowsync";
}

export type UploadValidationPreviewResult =
  | { outcome: "staging_unavailable"; title: string; message: string }
  | { outcome: "invalid"; title: string; message: string; issueCode: string | null; field: string | null };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSafeString(value: unknown, maximum = 256): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum && !/[\u0000-\u001f\u007f]/.test(value);
}

function isTimestamp(value: unknown): value is string {
  return isSafeString(value, 64) && !Number.isNaN(Date.parse(value));
}

function isStage(value: unknown): value is string {
  return typeof value === "string" && (UPLOAD_STAGE_CODES as readonly string[]).includes(value);
}

function isSafeFilename(value: unknown): value is string {
  return isSafeString(value, 256) && !/[\\/]/.test(value) && value !== "." && value !== "..";
}

function isStatus(value: unknown): value is UploadProcessingStatus {
  return typeof value === "string" && (UPLOAD_STATUSES as readonly string[]).includes(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowed: readonly string[]): boolean {
  const set = new Set(allowed);
  return Object.keys(value).every((key) => set.has(key));
}

function nullableString(value: unknown, maximum = 128): string | null | undefined {
  if (value === null || value === undefined) return value;
  return isSafeString(value, maximum) ? value : undefined;
}

function parseFailure(value: unknown): UploadFailure | null | undefined {
  if (value === null) return null;
  if (!isRecord(value) || !hasOnlyKeys(value, ["code", "summary"]) || Object.keys(value).length !== 2) return undefined;
  if (!isSafeString(value.code, 64) || !isSafeString(value.summary, 256)) return undefined;
  return { code: value.code, summary: value.summary };
}

export function parseUploadProgress(value: unknown): UploadProgressSummary | null {
  const keys = [
    "upload_id", "document_id", "status", "current_stage", "stage_label", "stage_sequence",
    "started_at", "updated_at", "completed_at", "progress_percent", "progress_approximate",
    "failure", "actor_label", "source_label",
  ];
  if (!isRecord(value) || !hasOnlyKeys(value, keys) || Object.keys(value).length !== keys.length) return null;
  const documentId = nullableString(value.document_id ?? null);
  const completedAt = value.completed_at === null ? null : isTimestamp(value.completed_at) ? value.completed_at : undefined;
  const actorLabel = nullableString(value.actor_label, 64);
  const sourceLabel = nullableString(value.source_label, 64);
  const failure = parseFailure(value.failure);
  const progress = value.progress_percent;
  if (
    !isSafeString(value.upload_id, 128) || documentId === undefined || !isStatus(value.status) ||
    !isStage(value.current_stage) || !isSafeString(value.stage_label, 64) ||
    !Number.isInteger(value.stage_sequence) || (value.stage_sequence as number) < 0 ||
    !isTimestamp(value.started_at) || !isTimestamp(value.updated_at) || completedAt === undefined ||
    !(progress === null || (Number.isInteger(progress) && (progress as number) >= 0 && (progress as number) <= 100)) ||
    typeof value.progress_approximate !== "boolean" || failure === undefined ||
    actorLabel === undefined || sourceLabel === undefined
  ) return null;
  return {
    uploadId: value.upload_id,
    documentId,
    status: value.status,
    currentStage: value.current_stage,
    stageLabel: value.stage_label,
    stageSequence: value.stage_sequence as number,
    startedAt: value.started_at,
    updatedAt: value.updated_at,
    completedAt,
    progressPercent: progress as number | null,
    progressApproximate: value.progress_approximate,
    failure,
    actorLabel,
    sourceLabel,
  };
}

function parseProgressEvent(value: unknown): UploadProgressEvent | null {
  if (!isRecord(value) || !hasOnlyKeys(value, ["stage", "status", "occurred_at", "summary"]) || Object.keys(value).length !== 4) return null;
  if (!isRecord(value.stage) || !hasOnlyKeys(value.stage, ["code", "label", "sequence", "completed", "occurred_at"]) || Object.keys(value.stage).length !== 5) return null;
  const stageOccurredAt = value.stage.occurred_at === null ? null : isTimestamp(value.stage.occurred_at) ? value.stage.occurred_at : undefined;
  if (
    !isStage(value.stage.code) || !isSafeString(value.stage.label, 64) ||
    !Number.isInteger(value.stage.sequence) || (value.stage.sequence as number) < 0 ||
    typeof value.stage.completed !== "boolean" || stageOccurredAt === undefined ||
    !isStatus(value.status) || !isTimestamp(value.occurred_at) || !isSafeString(value.summary, 256)
  ) return null;
  return {
    stage: {
      code: value.stage.code, label: value.stage.label, sequence: value.stage.sequence as number,
      completed: value.stage.completed, occurredAt: stageOccurredAt,
    },
    status: value.status,
    occurredAt: value.occurred_at,
    summary: value.summary,
  };
}

export function parseUploadTimeline(value: unknown): UploadTimeline | null {
  if (!isRecord(value) || !hasOnlyKeys(value, ["upload_id", "events"]) || Object.keys(value).length !== 2) return null;
  if (!isSafeString(value.upload_id, 128) || !Array.isArray(value.events) || value.events.length > 100) return null;
  const events = value.events.map(parseProgressEvent);
  if (events.some((event) => event === null)) return null;
  return { uploadId: value.upload_id, events: events as UploadProgressEvent[] };
}

export function parseUploadSummary(value: unknown): UploadSummary | null {
  const allowed = [
    "upload_id", "document_id", "filename", "file_type", "file_size_bytes", "source", "status",
    "received_at", "updated_at", "completed_at", "failure_code", "actor_label",
    "progress_is_derivable", "processing",
  ];
  if (!isRecord(value) || !hasOnlyKeys(value, allowed)) return null;
  const documentId = nullableString(value.document_id ?? null);
  const processing = value.processing === undefined ? null : parseUploadProgress(value.processing);
  const updatedAtValid = value.updated_at === undefined || isTimestamp(value.updated_at);
  const completedAtValid = value.completed_at === undefined || value.completed_at === null || isTimestamp(value.completed_at);
  const failureCodeValid = value.failure_code === undefined || value.failure_code === null || isSafeString(value.failure_code, 64);
  const actorLabelValid = value.actor_label === undefined || value.actor_label === null || isSafeString(value.actor_label, 64);
  const derivableValid = value.progress_is_derivable === undefined || typeof value.progress_is_derivable === "boolean";
  if (
    !isSafeString(value.upload_id, 128) || documentId === undefined || !isSafeFilename(value.filename) ||
    !isSafeString(value.file_type, 32) || !Number.isInteger(value.file_size_bytes) || (value.file_size_bytes as number) < 0 ||
    !isSafeString(value.source, 64) || !isStatus(value.status) || !isTimestamp(value.received_at) ||
    !updatedAtValid || !completedAtValid || !failureCodeValid || !actorLabelValid || !derivableValid ||
    (processing === null && value.processing !== undefined)
  ) return null;
  return {
    uploadId: value.upload_id, documentId, filename: value.filename, fileType: value.file_type,
    fileSizeBytes: value.file_size_bytes as number, source: value.source, status: value.status,
    receivedAt: value.received_at, processing,
  };
}
