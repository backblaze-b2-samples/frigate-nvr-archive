"use client";

import { Download, MapPin, Clock } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { EventView } from "@frigate-nvr-archive/shared";
import { API_BASE } from "@/lib/api-client";

interface EventDetailDialogProps {
  event: EventView | null;
  onOpenChange: (open: boolean) => void;
}

export function EventDetailDialog({
  event,
  onOpenChange,
}: EventDetailDialogProps) {
  return (
    <Dialog open={!!event} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        {event ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Badge variant="secondary" className="capitalize">
                  {event.label}
                </Badge>
                <span className="text-sm font-normal text-muted-foreground">
                  {event.camera}
                </span>
              </DialogTitle>
              <DialogDescription className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {new Date(event.start_time).toLocaleString()}
                </span>
                <span>score {(event.score * 100).toFixed(0)}%</span>
                {event.zones.length > 0 ? (
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {event.zones.join(", ")}
                  </span>
                ) : null}
              </DialogDescription>
            </DialogHeader>

            {/* Clip streams straight from B2 via a short-lived presigned URL. */}
            {event.clip_url ? (
              <video
                src={event.clip_url}
                controls
                poster={event.snapshot_url ?? undefined}
                className="w-full rounded-md bg-black"
              />
            ) : event.snapshot_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={event.snapshot_url}
                alt={`${event.label} on ${event.camera}`}
                className="w-full rounded-md"
              />
            ) : (
              <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                No media archived for this event.
              </div>
            )}

            {event.has_clip ? (
              <div className="flex justify-end">
                <Button asChild variant="outline" size="sm">
                  <a
                    href={`${API_BASE}/events/${event.id}/clip`}
                    rel="noopener noreferrer"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download clip from B2
                  </a>
                </Button>
              </div>
            ) : null}
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
