import { ArchiveLibrary } from "@/components/archive/archive-library";

export default function ArchivePage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Archive Library</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Browse this app&apos;s own archive on Backblaze B2, grouped by camera
          and date — recordings, event clips, and snapshots. A scoped view of
          the <code className="font-mono">frigate-nvr-archive/</code> prefix,
          distinct from the full-bucket Files explorer.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <ArchiveLibrary />
      </div>
    </div>
  );
}
