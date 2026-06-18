import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Import a clip</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Bring an external clip or snapshot into the archive — footage from
          another NVR, a phone, or a dashcam. It lands under this app&apos;s B2
          prefix and shows up in the Archive Library. Live Frigate footage
          arrives automatically via the archive worker. Up to 500 MB per file.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
