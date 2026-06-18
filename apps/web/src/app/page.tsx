import Link from "next/link";
import { Video } from "lucide-react";

import { Button } from "@/components/ui/button";
import { NvrStatsCards } from "@/components/dashboard/nvr-stats-cards";
import { WriteVolumeChart } from "@/components/dashboard/write-volume-chart";
import { RecentEventsTable } from "@/components/dashboard/recent-events-table";
import { ObjectClassBreakdown } from "@/components/dashboard/object-class-breakdown";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">NVR Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your Frigate surveillance archive at a glance — cameras, detection
            events, and footage continuously written to Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/events">
            <Video className="h-3.5 w-3.5" />
            Browse events
          </Link>
        </Button>
      </div>
      <NvrStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <WriteVolumeChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <ObjectClassBreakdown />
        </div>
      </div>
      <div className="animate-fade-in-up stagger-5">
        <RecentEventsTable />
      </div>
    </div>
  );
}
