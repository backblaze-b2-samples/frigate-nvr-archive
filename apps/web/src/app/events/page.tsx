import { EventTimeline } from "@/components/events/event-timeline";
import { ArchiveNowButton } from "@/components/events/archive-now-button";

export default function EventsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Events</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Search the Frigate detection timeline — filter by camera, object
            class, and date. Snapshots and clips stream straight from Backblaze
            B2 via short-lived presigned URLs.
          </p>
        </div>
        <ArchiveNowButton />
      </div>
      <div className="animate-fade-in-up stagger-2">
        <EventTimeline />
      </div>
    </div>
  );
}
