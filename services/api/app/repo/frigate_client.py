"""HTTP adapter for a real Frigate NVR.

Frigate is the detection engine. This module is the ONLY place that talks to
Frigate, and it does so over Frigate's documented HTTP API — it never runs object
detection itself (no ultralytics/YOLO/torch here). It is a `repo/` adapter like
`b2_client`, but it speaks to Frigate via `httpx`, not boto3, so the structural
boto3-containment test does not apply to it.

Frigate API surface used:
  GET /api/events?...                  list recently-ended detection events
  GET /api/events/<id>/clip.mp4        the event's recorded clip
  GET /api/events/<id>/snapshot.jpg    the event's best-frame snapshot
  GET /api/version                     liveness probe

Docs: https://docs.frigate.video/integrations/api/
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Identify ourselves to Frigate the same way we identify to B2.
_USER_AGENT = "b2ai-frigate-nvr-archive"
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _base_url() -> str:
    return settings.frigate_url.rstrip("/")


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=_base_url(),
        timeout=_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
    )


def is_available() -> bool:
    """True if Frigate answers its version endpoint. Used by /health."""
    try:
        with _client() as c:
            resp = c.get("/api/version")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


def list_events(limit: int = 50, after: float | None = None) -> list[dict]:
    """Return recently-ended Frigate events (raw API dicts), newest first.

    `after` is a Unix timestamp; when given, only events that started after it
    are returned (used to avoid re-archiving the same events on each poll).
    """
    params: dict = {"limit": limit, "include_thumbnails": 0, "in_progress": 0}
    if after is not None:
        params["after"] = after
    try:
        with _client() as c:
            resp = c.get("/api/events", params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Frigate event list failed: {e}") from e
    if not isinstance(data, list):
        raise RuntimeError("Frigate /api/events returned an unexpected payload")
    return data


def download_clip(event_id: str) -> bytes | None:
    """Download an event's recorded clip (mp4). None if Frigate has no clip."""
    return _download(f"/api/events/{event_id}/clip.mp4")


def download_snapshot(event_id: str) -> bytes | None:
    """Download an event's snapshot (jpg). None if Frigate has no snapshot."""
    return _download(f"/api/events/{event_id}/snapshot.jpg")


def _download(path: str) -> bytes | None:
    try:
        with _client() as c:
            resp = c.get(path)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError as e:
        raise RuntimeError(f"Frigate download failed for '{path}': {e}") from e
