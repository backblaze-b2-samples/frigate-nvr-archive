"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  archiveNow,
  deleteFile,
  getArchiveCameraDates,
  getArchiveOverview,
  getEvent,
  getFiles,
  getFileStats,
  getNvrStats,
  getPreviewUrl,
  getUploadActivity,
  getWriteVolume,
  searchEvents,
} from "@/lib/api-client";
import type {
  EventSearchParams,
  FileMetadata,
} from "@frigate-nvr-archive/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  nvrStats: () => [...qk.all, "nvr-stats"] as const,
  writeVolume: (days: number) => [...qk.all, "write-volume", days] as const,
  events: (params: EventSearchParams) =>
    [...qk.all, "events", params] as const,
  event: (id: string) => [...qk.all, "event", id] as const,
  archive: () => [...qk.all, "archive"] as const,
  archiveDates: (camera: string) =>
    [...qk.all, "archive", "dates", camera] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Frigate NVR archive ---

export function useNvrStats() {
  return useQuery({
    queryKey: qk.nvrStats(),
    queryFn: getNvrStats,
  });
}

export function useWriteVolume(days = 7) {
  return useQuery({
    queryKey: qk.writeVolume(days),
    queryFn: () => getWriteVolume(days),
  });
}

export function useEvents(params: EventSearchParams) {
  return useQuery({
    queryKey: qk.events(params),
    queryFn: () => searchEvents(params),
  });
}

export function useEvent(id: string | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.event(id ?? ""),
    queryFn: () => getEvent(id as string),
    enabled: enabled && !!id,
    staleTime: 60_000,
  });
}

export function useArchiveOverview() {
  return useQuery({
    queryKey: qk.archive(),
    queryFn: getArchiveOverview,
  });
}

export function useArchiveCameraDates(camera: string | undefined) {
  return useQuery({
    queryKey: qk.archiveDates(camera ?? ""),
    queryFn: () => getArchiveCameraDates(camera as string),
    enabled: !!camera,
  });
}

/** Trigger a one-shot Frigate -> B2 sync, then refresh every B2-backed view. */
export function useArchiveNow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => archiveNow(),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}
