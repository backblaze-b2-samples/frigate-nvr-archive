"""B2 (S3) data access for the Frigate NVR archive.

Every key lives under `settings.archive_prefix`. The searchable event index is a
set of JSONL objects in B2 (`<prefix>index/<YYYY-MM-DD>.jsonl`, one event per
line) — that index, plus the media objects themselves, IS the data store; there
is no database. boto3 stays confined to this layer.

B2 object layout (scoped to settings.archive_prefix):
  recordings/<camera>/<YYYY-MM-DD>/<HH>/<segment>.mp4
  events/<camera>/<event_id>/clip.mp4
  events/<camera>/<event_id>/snapshot.jpg
  index/<YYYY-MM-DD>.jsonl
  index/cameras.json
"""

import json
import logging
from datetime import UTC, date, datetime, timedelta

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.types import ArchiveEvent

logger = logging.getLogger(__name__)


# ----- Key builders (scoped to settings.archive_prefix) -----


def _p() -> str:
    return settings.archive_prefix


def event_clip_key(camera: str, event_id: str) -> str:
    return f"{_p()}events/{_safe(camera)}/{event_id}/clip.mp4"


def event_snapshot_key(camera: str, event_id: str) -> str:
    return f"{_p()}events/{_safe(camera)}/{event_id}/snapshot.jpg"


def recording_key(camera: str, day: str, hour: str, segment: str) -> str:
    return f"{_p()}recordings/{_safe(camera)}/{day}/{hour}/{segment}"


def index_key(day: str) -> str:
    return f"{_p()}index/{day}.jsonl"


def cameras_key() -> str:
    return f"{_p()}index/cameras.json"


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


# ----- Object IO -----


def put_bytes(key: str, data: bytes, content_type: str) -> int:
    """Upload raw bytes to B2; returns byte count. Raises RuntimeError on fail."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    return len(data)


def get_bytes(key: str) -> bytes | None:
    """Download an object's bytes. Returns None if it doesn't exist."""
    client = get_s3_client()
    try:
        resp = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return resp["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e


def presign_get(key: str, expires_in: int = 600) -> str:
    """Presigned GET URL for inline playback/preview (no attachment header)."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def presign_download(key: str, filename: str, expires_in: int = 600) -> str:
    """Presigned GET URL that downloads as an attachment (clip export)."""
    client = get_s3_client()
    params = {
        "Bucket": settings.b2_bucket_name,
        "Key": key,
        "ResponseContentDisposition": f'attachment; filename="{filename}"',
    }
    try:
        return client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


# ----- JSONL event index -----


def append_event(event: ArchiveEvent) -> None:
    """Append one event to its day's JSONL index partition in B2.

    B2 has no native append, so we read-modify-write the day partition. The
    archive worker is single-writer, so this is safe for the sample's scale.
    """
    day = event.start_time.astimezone(UTC).date().isoformat()
    key = index_key(day)
    existing = get_bytes(key) or b""
    line = event.model_dump_json().encode("utf-8")
    body = existing + line + b"\n" if existing else line + b"\n"
    put_bytes(key, body, "application/x-ndjson")


def read_index_day(day: str) -> list[ArchiveEvent]:
    """Load and parse one day's JSONL index partition. Empty if absent."""
    raw = get_bytes(index_key(day))
    if not raw:
        return []
    events: list[ArchiveEvent] = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(ArchiveEvent.model_validate_json(line))
        except ValueError:
            logger.warning("Skipping corrupt index line in %s", day)
    return events


def read_index_range(start: date, end: date) -> list[ArchiveEvent]:
    """Load every event across an inclusive day range from B2."""
    events: list[ArchiveEvent] = []
    cur = start
    while cur <= end:
        events.extend(read_index_day(cur.isoformat()))
        cur += timedelta(days=1)
    return events


def list_index_days() -> list[str]:
    """List every `index/<day>.jsonl` partition present in B2 (YYYY-MM-DD), desc."""
    prefix = f"{_p()}index/"
    days: list[str] = []
    for key in _list_keys(prefix):
        name = key[len(prefix):]
        if name.endswith(".jsonl"):
            days.append(name[: -len(".jsonl")])
    days.sort(reverse=True)
    return days


def write_cameras(payload: dict) -> None:
    put_bytes(
        cameras_key(),
        json.dumps(payload, default=str).encode("utf-8"),
        "application/json",
    )


def read_cameras() -> dict:
    raw = get_bytes(cameras_key())
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


# ----- Scoped listing & deletion -----


def list_objects(prefix: str) -> list[dict]:
    """List objects under a prefix as {key, size, last_modified} dicts.

    Always scoped under the archive prefix by callers; paginated.
    """
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                out.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return out


def _list_keys(prefix: str) -> list[str]:
    return [o["key"] for o in list_objects(prefix)]


def delete_prefix(prefix: str) -> int:
    """Delete every object under `prefix`. Caller MUST scope this to the
    archive prefix; never touches the full bucket or other apps' data.
    Returns the number of objects removed.
    """
    if not prefix.startswith(_p()):
        raise RuntimeError(
            f"Refusing to delete outside archive prefix: '{prefix}'"
        )
    client = get_s3_client()
    deleted = 0
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            objects = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
            if objects:
                client.delete_objects(
                    Bucket=settings.b2_bucket_name,
                    Delete={"Objects": objects},
                )
                deleted += len(objects)
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 scoped delete failed for '{prefix}': {e}") from e
    return deleted


def now_utc() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "append_event",
    "cameras_key",
    "delete_prefix",
    "event_clip_key",
    "event_snapshot_key",
    "get_bytes",
    "index_key",
    "list_index_days",
    "list_objects",
    "now_utc",
    "presign_download",
    "presign_get",
    "put_bytes",
    "read_cameras",
    "read_index_day",
    "read_index_range",
    "recording_key",
    "write_cameras",
]
