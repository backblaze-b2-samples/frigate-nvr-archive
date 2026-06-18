"""Domain models for the Frigate NVR archive.

Every model here is a plain Pydantic model — no Frigate-SDK or boto3 types leak
in. The archive's sole data store is Backblaze B2: detection events are appended
to JSONL index partitions (`<prefix>index/<YYYY-MM-DD>.jsonl`) and media (clips,
snapshots, recording segments) lives under the same prefix. There is no database.
"""

from datetime import datetime

from pydantic import BaseModel


class ArchiveEvent(BaseModel):
    """One Frigate detection event, as archived to B2.

    Serialized as a single JSON line in `<prefix>index/<YYYY-MM-DD>.jsonl`. The
    `*_key` fields point at the media this app copied to B2; the `has_*` flags
    let the UI decide which playback controls to render without a HEAD round-trip.
    """

    id: str
    camera: str
    label: str
    score: float
    zones: list[str] = []
    start_time: datetime
    end_time: datetime | None = None
    # B2 object keys (scoped to the archive prefix) for the media this app
    # copied from Frigate. None until the worker has shipped that artifact.
    clip_key: str | None = None
    snapshot_key: str | None = None
    has_clip: bool = False
    has_snapshot: bool = False
    # Byte sizes of the archived media, for footprint/write-rate stats.
    clip_bytes: int = 0
    snapshot_bytes: int = 0
    archived_at: datetime


class EventView(ArchiveEvent):
    """An ArchiveEvent enriched with short-lived presigned playback URLs.

    Returned by the timeline/search API so the browser can stream the clip and
    render the snapshot straight from B2 with no egress through a vendor cloud.
    """

    clip_url: str | None = None
    snapshot_url: str | None = None


class EventFilters(BaseModel):
    """Search filters for the event timeline (all optional)."""

    camera: str | None = None
    label: str | None = None
    zone: str | None = None
    start_date: str | None = None  # YYYY-MM-DD inclusive
    end_date: str | None = None  # YYYY-MM-DD inclusive
    limit: int = 100


class CameraSummary(BaseModel):
    """Per-camera roll-up for the dashboard and Archive Library."""

    name: str
    event_count: int = 0
    last_event_at: datetime | None = None
    archived_bytes: int = 0
    archived_bytes_human: str = "0 B"


class NvrStats(BaseModel):
    """Dashboard aggregates across the whole archive prefix on B2."""

    cameras: int
    events_total: int
    events_today: int
    footage_bytes: int
    footage_bytes_human: str
    bytes_today: int
    bytes_today_human: str
    label_counts: dict[str, int] = {}
    camera_summaries: list[CameraSummary] = []
    recent_events: list["EventSummary"] = []


class EventSummary(BaseModel):
    """Lightweight projection for dashboard recent-events and search lists."""

    id: str
    camera: str
    label: str
    score: float
    zones: list[str] = []
    start_time: datetime
    has_clip: bool = False
    has_snapshot: bool = False


class DailyWriteVolume(BaseModel):
    """One day's bytes-written-to-B2 figure for the write-rate chart."""

    date: str
    bytes_written: int
    bytes_written_human: str
