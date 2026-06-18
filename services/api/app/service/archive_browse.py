"""Archive Library — the sample-specific scoped explorer.

Browses ONLY this app's `settings.archive_prefix` on B2 (distinct from the
full-bucket /files explorer), grouped by camera and date, split into recordings /
clips / snapshots. Backed entirely by `list_objects_v2` over the scoped prefix.
"""

import logging
import re
from collections import defaultdict

from app.config import settings
from app.repo import archive_store as store
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

# events/<camera>/<event_id>/<file>
_EVENT_RE = re.compile(r"^events/([^/]+)/([^/]+)/(.+)$")
# recordings/<camera>/<YYYY-MM-DD>/<HH>/<segment>
_RECORDING_RE = re.compile(r"^recordings/([^/]+)/([^/]+)/([^/]+)/(.+)$")


class ArchiveBrowseError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _rel(key: str) -> str:
    return key[len(settings.archive_prefix):]


def list_cameras() -> list[dict]:
    """Distinct cameras seen across recordings + events, with object/byte totals."""
    objects = store.list_objects(settings.archive_prefix)
    per_camera: dict[str, dict] = defaultdict(
        lambda: {"objects": 0, "bytes": 0, "clips": 0, "snapshots": 0, "recordings": 0}
    )
    for obj in objects:
        rel = _rel(obj["key"])
        cam, kind = _classify(rel)
        if cam is None:
            continue
        bucket = per_camera[cam]
        bucket["objects"] += 1
        bucket["bytes"] += obj["size"]
        if kind:
            bucket[kind] += 1
    return [
        {
            "name": cam,
            "objects": v["objects"],
            "bytes": v["bytes"],
            "bytes_human": humanize_bytes(v["bytes"]),
            "clips": v["clips"],
            "snapshots": v["snapshots"],
            "recordings": v["recordings"],
        }
        for cam, v in sorted(per_camera.items(), key=lambda kv: -kv[1]["bytes"])
    ]


def _classify(rel: str) -> tuple[str | None, str | None]:
    """Return (camera, kind) for a relative archive key. kind is one of
    clips/snapshots/recordings, or None for index/other objects."""
    m = _EVENT_RE.match(rel)
    if m:
        camera, _event_id, fname = m.groups()
        if fname.endswith(".mp4"):
            return camera, "clips"
        if fname.endswith((".jpg", ".jpeg")):
            return camera, "snapshots"
        return camera, None
    m = _RECORDING_RE.match(rel)
    if m:
        return m.group(1), "recordings"
    return None, None


def list_camera_dates(camera: str) -> list[dict]:
    """For one camera, list dates with per-date object/byte counts.

    Dates come from recording day folders and from event start days inferred via
    the JSONL index (events are keyed by id, not date, so we use the index).
    """
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in camera)
    counts: dict[str, dict] = defaultdict(lambda: {"objects": 0, "bytes": 0})

    rec_prefix = f"{settings.archive_prefix}recordings/{safe}/"
    for obj in store.list_objects(rec_prefix):
        rel = obj["key"][len(rec_prefix):]
        day = rel.split("/", 1)[0]
        counts[day]["objects"] += 1
        counts[day]["bytes"] += obj["size"]

    for day in store.list_index_days():
        for e in store.read_index_day(day):
            if e.camera != camera:
                continue
            counts[day]["objects"] += int(e.has_clip) + int(e.has_snapshot)
            counts[day]["bytes"] += e.clip_bytes + e.snapshot_bytes

    return [
        {
            "date": day,
            "objects": v["objects"],
            "bytes": v["bytes"],
            "bytes_human": humanize_bytes(v["bytes"]),
        }
        for day, v in sorted(counts.items(), reverse=True)
    ]


def get_overview() -> dict:
    """Top-level Archive Library payload: prefix + per-camera roll-up."""
    return {
        "prefix": settings.archive_prefix,
        "cameras": list_cameras(),
    }
