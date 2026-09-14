import type { components } from "@/lib/api/schema";

export type DownloadItem = components["schemas"]["DownloadItemResponse"];
export type DownloadsPage = components["schemas"]["DownloadsPage"];
export type DownloadCategory = "all" | "contacts" | "analytics" | "chat_history" | "campaigns";
export type DownloadStatus = "all" | "pending" | "processing" | "ready" | "failed" | "expired";

export interface DownloadQuery {
  category: DownloadCategory;
  status: DownloadStatus;
  cursor?: string;
}

export const DOWNLOAD_STATUSES: Exclude<DownloadStatus, "all">[] = [
  "pending",
  "processing",
  "ready",
  "failed",
  "expired",
];

export const DOWNLOAD_STATUS_LABELS: Record<DownloadStatus, string> = {
  all: "All statuses",
  pending: "Queued",
  processing: "Preparing",
  ready: "Ready",
  failed: "Failed",
  expired: "Expired",
};
