export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Frigate NVR archive ---

/** One archived Frigate detection event, enriched with presigned playback URLs
 * (the EventView the API returns). Media streams straight from B2. */
export interface EventView {
  id: string;
  camera: string;
  label: string;
  score: number;
  zones: string[];
  start_time: string;
  end_time: string | null;
  clip_key: string | null;
  snapshot_key: string | null;
  has_clip: boolean;
  has_snapshot: boolean;
  clip_bytes: number;
  snapshot_bytes: number;
  archived_at: string;
  clip_url: string | null;
  snapshot_url: string | null;
}

export interface EventSummary {
  id: string;
  camera: string;
  label: string;
  score: number;
  zones: string[];
  start_time: string;
  has_clip: boolean;
  has_snapshot: boolean;
}

export interface CameraSummary {
  name: string;
  event_count: number;
  last_event_at: string | null;
  archived_bytes: number;
  archived_bytes_human: string;
}

export interface NvrStats {
  cameras: number;
  events_total: number;
  events_today: number;
  footage_bytes: number;
  footage_bytes_human: string;
  bytes_today: number;
  bytes_today_human: string;
  label_counts: Record<string, number>;
  camera_summaries: CameraSummary[];
  recent_events: EventSummary[];
}

export interface DailyWriteVolume {
  date: string;
  bytes_written: number;
  bytes_written_human: string;
}

export interface EventSearchParams {
  camera?: string;
  label?: string;
  zone?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}

/** Archive Library (scoped explorer) payloads. */
export interface ArchiveCamera {
  name: string;
  objects: number;
  bytes: number;
  bytes_human: string;
  clips: number;
  snapshots: number;
  recordings: number;
}

export interface ArchiveOverview {
  prefix: string;
  cameras: ArchiveCamera[];
}

export interface ArchiveDate {
  date: string;
  objects: number;
  bytes: number;
  bytes_human: string;
}

export interface ArchiveResult {
  scanned: number;
  archived: number;
  bytes: number;
}
