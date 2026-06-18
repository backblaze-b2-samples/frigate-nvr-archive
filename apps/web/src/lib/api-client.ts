import type {
  ArchiveDate,
  ArchiveOverview,
  ArchiveResult,
  DailyUploadCount,
  DailyWriteVolume,
  EventSearchParams,
  EventView,
  FileMetadata,
  FileUploadResponse,
  NvrStats,
  UploadStats,
} from "@frigate-nvr-archive/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

/** Default per-request timeout. Bounds any single call so the UI never hangs
 * on a stalled request; callers can override via `timeoutMs`. */
const DEFAULT_TIMEOUT_MS = 60_000;

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...requestInit } = init ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...requestInit,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Request timed out — please try again", 408);
    }
    // Network failure (offline, DNS, CORS, etc.)
    throw new ApiError("Network error — check your connection", 0);
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

export async function getHealth() {
  return apiFetch<{
    status: string;
    b2_connected: boolean;
    frigate_connected: boolean;
  }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetch<FileMetadata>(`/files/${key}`);
}

export async function getDownloadUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/download`);
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/preview`);
}

export async function deleteFile(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/files/${key}`, {
    method: "DELETE",
  });
}

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}/upload`);
    xhr.send(formData);
  });
}

// --- Frigate NVR archive ---

export async function getNvrStats() {
  return apiFetch<NvrStats>("/events/stats");
}

export async function getWriteVolume(days = 7) {
  return apiFetch<DailyWriteVolume[]>(
    `/events/stats/write-volume?days=${days}`
  );
}

export async function searchEvents(params: EventSearchParams) {
  const q = new URLSearchParams();
  if (params.camera) q.set("camera", params.camera);
  if (params.label) q.set("label", params.label);
  if (params.zone) q.set("zone", params.zone);
  if (params.start_date) q.set("start_date", params.start_date);
  if (params.end_date) q.set("end_date", params.end_date);
  if (params.limit) q.set("limit", String(params.limit));
  return apiFetch<EventView[]>(`/events?${q.toString()}`);
}

export async function getEvent(id: string) {
  return apiFetch<EventView>(`/events/${id}`);
}

export async function getEventClipUrl(id: string) {
  return apiFetch<{ url: string }>(`/events/${id}/clip`);
}

/** Trigger a one-shot Frigate -> B2 sync (the worker does this on a loop). */
export async function archiveNow() {
  return apiFetch<ArchiveResult>("/events/archive", { method: "POST" });
}

export async function getArchiveOverview() {
  return apiFetch<ArchiveOverview>("/archive");
}

export async function getArchiveCameraDates(camera: string) {
  return apiFetch<ArchiveDate[]>(
    `/archive/cameras/${encodeURIComponent(camera)}/dates`
  );
}
