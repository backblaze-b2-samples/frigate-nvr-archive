"""NVR dashboard aggregation.

Rolls the JSONL event index in B2 up into headline metrics: cameras, events
today, footage archived to B2 (GB), today's write volume, the object-class mix,
per-camera summaries, and a recent-events list — plus a daily write-rate series
for the dashboard chart. All reads come from B2; there is no database.
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.repo import archive_store as store
from app.types import (
    ArchiveEvent,
    CameraSummary,
    DailyWriteVolume,
    EventSummary,
    NvrStats,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

RECENT_LIMIT = 10
# How many recent index partitions the dashboard scans. Keeps the read bounded
# even when the archive spans years of daily partitions.
DASHBOARD_LOOKBACK_DAYS = 30


def _recent_events(days: int) -> list[ArchiveEvent]:
    today = datetime.now(UTC).date()
    start = today - timedelta(days=days - 1)
    return store.read_index_range(start, today)


def _summary(event: ArchiveEvent) -> EventSummary:
    return EventSummary(
        id=event.id,
        camera=event.camera,
        label=event.label,
        score=event.score,
        zones=event.zones,
        start_time=event.start_time,
        has_clip=event.has_clip,
        has_snapshot=event.has_snapshot,
    )


def get_nvr_stats() -> NvrStats:
    events = _recent_events(DASHBOARD_LOOKBACK_DAYS)
    today = datetime.now(UTC).date()

    events_today = 0
    bytes_today = 0
    footage_bytes = 0
    label_counts: dict[str, int] = defaultdict(int)
    per_camera: dict[str, CameraSummary] = {}

    for e in events:
        ev_bytes = e.clip_bytes + e.snapshot_bytes
        footage_bytes += ev_bytes
        label_counts[e.label] += 1
        if e.start_time.astimezone(UTC).date() == today:
            events_today += 1
            bytes_today += ev_bytes
        cam = per_camera.get(e.camera) or CameraSummary(name=e.camera)
        cam.event_count += 1
        cam.archived_bytes += ev_bytes
        if cam.last_event_at is None or e.start_time > cam.last_event_at:
            cam.last_event_at = e.start_time
        per_camera[e.camera] = cam

    for cam in per_camera.values():
        cam.archived_bytes_human = humanize_bytes(cam.archived_bytes)

    recent = sorted(events, key=lambda e: e.start_time, reverse=True)[:RECENT_LIMIT]

    return NvrStats(
        cameras=len(per_camera),
        events_total=len(events),
        events_today=events_today,
        footage_bytes=footage_bytes,
        footage_bytes_human=humanize_bytes(footage_bytes),
        bytes_today=bytes_today,
        bytes_today_human=humanize_bytes(bytes_today),
        label_counts=dict(sorted(label_counts.items(), key=lambda kv: -kv[1])),
        camera_summaries=sorted(
            per_camera.values(), key=lambda c: -c.event_count
        ),
        recent_events=[_summary(e) for e in recent],
    )


def get_write_volume(days: int = 7) -> list[DailyWriteVolume]:
    """Daily bytes-written-to-B2 series for the write-rate chart."""
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)
    events = store.read_index_range(cutoff, today)

    per_day: dict[str, int] = defaultdict(int)
    for e in events:
        day = e.start_time.astimezone(UTC).date().isoformat()
        per_day[day] += e.clip_bytes + e.snapshot_bytes

    out: list[DailyWriteVolume] = []
    for i in range(days):
        day = (cutoff + timedelta(days=i)).isoformat()
        b = per_day.get(day, 0)
        out.append(
            DailyWriteVolume(
                date=day, bytes_written=b, bytes_written_human=humanize_bytes(b)
            )
        )
    return out
