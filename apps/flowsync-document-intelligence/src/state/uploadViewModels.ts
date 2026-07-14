import type { UploadMetadataPreviewRequest, UploadProgressSummary, UploadSummary } from "../types/upload";

const SUPPORTED_TYPES = new Set(["pdf", "csv", "xlsx", "txt", "eml"]);

export interface SelectedUploadMetadata {
  filename: string;
  sizeBytes: number;
  sizeLabel: string;
  fileType: string;
  contentType: string | null;
  browserHint: "supported" | "unsupported" | "empty";
}

export function toSelectedUploadMetadata(file: File): SelectedUploadMetadata {
  const filename = file.name.slice(0, 512);
  const extension = filename.includes(".") ? filename.split(".").pop()?.toLowerCase() ?? "unknown" : "unknown";
  const browserHint = file.size === 0 ? "empty" : SUPPORTED_TYPES.has(extension) ? "supported" : "unsupported";
  return {
    filename,
    sizeBytes: file.size,
    sizeLabel: formatFileSize(file.size),
    fileType: extension,
    contentType: file.type && file.type.length <= 128 ? file.type : null,
    browserHint,
  };
}

export function toUploadPreviewRequest(metadata: SelectedUploadMetadata): UploadMetadataPreviewRequest {
  return {
    filename: metadata.filename,
    file_size_bytes: metadata.sizeBytes,
    file_type: metadata.fileType,
    ...(metadata.contentType ? { declared_content_type: metadata.contentType } : {}),
    source: "flowsync",
  };
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatUploadTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Time unavailable" : parsed.toLocaleString();
}

export function statusLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export interface RecentUploadViewModel {
  id: string;
  documentId: string | null;
  filename: string;
  typeAndSize: string;
  status: string;
  statusLabel: string;
  receivedAt: string;
  progress: UploadProgressSummary | null;
}

export function toRecentUploadViewModel(upload: UploadSummary): RecentUploadViewModel {
  return {
    id: upload.uploadId,
    documentId: upload.documentId,
    filename: upload.filename,
    typeAndSize: `${upload.fileType.toUpperCase()} · ${formatFileSize(upload.fileSizeBytes)}`,
    status: upload.status,
    statusLabel: statusLabel(upload.status),
    receivedAt: formatUploadTime(upload.receivedAt),
    progress: upload.processing,
  };
}
