"use client";

import { useState } from "react";
import { Camera, ChevronDown, ChevronRight, FolderArchive } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useArchiveOverview } from "@/lib/queries";
import { CameraDates } from "./camera-dates";

export function ArchiveLibrary() {
  const { data, isLoading, error, refetch } = useArchiveOverview();
  const [open, setOpen] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-md" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cameras = data?.cameras ?? [];

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-muted/30 px-4 py-2.5 text-xs text-muted-foreground">
        Scoped to{" "}
        <code className="font-mono text-foreground">{data?.prefix}</code> on B2 —
        this is the sample&apos;s own prefix, not the whole bucket (see Files for
        that).
      </div>

      {cameras.length === 0 ? (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={FolderArchive}
              title="Nothing archived yet"
              description="Run the archive worker to stream Frigate recordings, clips, and snapshots into this prefix on B2."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {cameras.map((cam) => {
            const isOpen = open === cam.name;
            return (
              <Card key={cam.name} className="overflow-hidden">
                <button
                  className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/40"
                  onClick={() => setOpen(isOpen ? null : cam.name)}
                >
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                  <Camera className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{cam.name}</span>
                  <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline">{cam.clips} clips</Badge>
                    <Badge variant="outline">{cam.snapshots} snapshots</Badge>
                    <Badge variant="outline">
                      {cam.recordings} recordings
                    </Badge>
                    <span className="tabular-nums font-medium text-foreground">
                      {cam.bytes_human}
                    </span>
                  </div>
                </button>
                {isOpen ? (
                  <div className="border-t border-border px-4 py-3">
                    <CameraDates camera={cam.name} />
                  </div>
                ) : null}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
