from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible) ---
    # All required; left empty so no region/endpoint is baked into source.
    # `main.py` startup validation (REQUIRED_B2_SETTINGS) fails fast with a
    # readable error if any is omitted. See .env.example for example values.
    b2_endpoint: str = ""
    b2_region: str = ""
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    # Optional public base URL for the bucket (only if it is public). Leave
    # blank to serve every clip/snapshot through short-lived presigned URLs.
    b2_public_url: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits. The /upload page imports external clips into the archive;
    # allow up to 500MB so longer manually-imported clips fit.
    max_file_size: int = 500 * 1024 * 1024  # 500MB

    # Small durable counter for the /files browser's download stats. Point at
    # a persistent volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # --- Frigate NVR (the detection engine; never re-implemented here) ---
    # Base URL of a running Frigate instance. The archive worker consumes its
    # HTTP API (/api/events, /api/events/<id>/clip.mp4, .../snapshot.jpg). See
    # infra/frigate/ for a docker-compose that brings up real Frigate.
    frigate_url: str = "http://localhost:5000"
    # RTSP/file input wired into Frigate via infra/frigate/config.yml. Surfaced
    # here only so the Settings screen / docs can echo what Frigate is watching.
    frigate_rtsp_input: str = ""

    # --- Archive worker (Frigate -> B2) ---
    # Seconds between event polls when the archive worker runs in a loop.
    archive_poll_interval_s: int = 30
    # How many recently-ended Frigate events to pull per poll.
    archive_event_limit: int = 50
    # How many new events a single on-demand UI sync ("Sync from Frigate")
    # archives before returning. Kept small so the request completes in seconds
    # and the button gets a prompt confirmation; the standing worker keeps the
    # full window up to date in the background. Repeated clicks drain the rest.
    archive_sync_limit: int = 5

    # --- B2 prefix scoping ---
    # Every object this app writes lives under this prefix. The /archive
    # library lists only this prefix; /files browses the full bucket. Search
    # reads the JSONL index partitions under `<archive_prefix>index/`.
    archive_prefix: str = "frigate-nvr-archive/"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()
