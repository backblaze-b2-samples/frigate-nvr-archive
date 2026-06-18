"use client";

import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { EventSearchParams } from "@frigate-nvr-archive/shared";

const ANY = "__any__";

interface EventFiltersBarProps {
  value: EventSearchParams;
  onChange: (next: EventSearchParams) => void;
  cameras: string[];
  labels: string[];
}

export function EventFiltersBar({
  value,
  onChange,
  cameras,
  labels,
}: EventFiltersBarProps) {
  const set = (patch: Partial<EventSearchParams>) =>
    onChange({ ...value, ...patch });

  const hasFilters =
    value.camera || value.label || value.start_date || value.end_date;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">Camera</Label>
          <Select
            value={value.camera || ANY}
            onValueChange={(v) => set({ camera: v === ANY ? undefined : v })}
          >
            <SelectTrigger className="h-9">
              <SelectValue placeholder="All cameras" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANY}>All cameras</SelectItem>
              {cameras.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">Object class</Label>
          <Select
            value={value.label || ANY}
            onValueChange={(v) => set({ label: v === ANY ? undefined : v })}
          >
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Any object" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANY}>Any object</SelectItem>
              {labels.map((l) => (
                <SelectItem key={l} value={l} className="capitalize">
                  {l}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">From</Label>
          <Input
            type="date"
            className="h-9"
            value={value.start_date ?? ""}
            onChange={(e) =>
              set({ start_date: e.target.value || undefined })
            }
          />
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">To</Label>
          <Input
            type="date"
            className="h-9"
            value={value.end_date ?? ""}
            onChange={(e) => set({ end_date: e.target.value || undefined })}
          />
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
        <Search className="h-3.5 w-3.5" />
        <span>
          Search reads the JSONL detection index straight from B2 — no database.
        </span>
        {hasFilters ? (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto h-7 text-xs"
            onClick={() => onChange({ limit: value.limit })}
          >
            <X className="h-3 w-3" />
            Clear
          </Button>
        ) : null}
      </div>
    </div>
  );
}
