"use client";

import { RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useArchiveNow } from "@/lib/queries";

export function ArchiveNowButton() {
  const { mutate, isPending } = useArchiveNow();

  return (
    <Button
      size="sm"
      className="h-8"
      disabled={isPending}
      onClick={() =>
        mutate(undefined, {
          onSuccess: (res) =>
            toast.success(
              `Synced ${res.archived} new event${res.archived === 1 ? "" : "s"} to B2`,
            ),
          onError: (e) => toast.error(e.message),
        })
      }
    >
      <RefreshCw className={`h-3.5 w-3.5 ${isPending ? "animate-spin" : ""}`} />
      {isPending ? "Syncing…" : "Sync from Frigate"}
    </Button>
  );
}
