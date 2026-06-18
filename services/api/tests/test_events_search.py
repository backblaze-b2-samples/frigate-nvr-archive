"""Unit tests for event timeline search over the JSONL index in B2."""

from datetime import UTC, datetime

from app.service import events as events_service
from app.types import ArchiveEvent, EventFilters


def _event(eid: str, camera: str, label: str, zones=None) -> ArchiveEvent:
    return ArchiveEvent(
        id=eid,
        camera=camera,
        label=label,
        score=0.8,
        zones=zones or [],
        start_time=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        archived_at=datetime(2026, 6, 1, 12, 0, 1, tzinfo=UTC),
        clip_key=f"frigate-nvr-archive/events/{camera}/{eid}/clip.mp4",
        snapshot_key=f"frigate-nvr-archive/events/{camera}/{eid}/snapshot.jpg",
        has_clip=True,
        has_snapshot=True,
    )


SAMPLE = [
    _event("1", "front_door", "person", ["porch"]),
    _event("2", "front_door", "car"),
    _event("3", "driveway", "person"),
]


def _patch_index(monkeypatch):
    monkeypatch.setattr(
        events_service.store, "read_index_range", lambda s, e: list(SAMPLE)
    )
    # Presigning is exercised elsewhere; stub it so no B2 call happens.
    monkeypatch.setattr(
        events_service.store, "presign_get", lambda key, **kw: f"https://signed/{key}"
    )


def test_filter_by_camera(monkeypatch):
    _patch_index(monkeypatch)
    out = events_service.search_events(EventFilters(camera="front_door"))
    assert {e.id for e in out} == {"1", "2"}


def test_filter_by_label(monkeypatch):
    _patch_index(monkeypatch)
    out = events_service.search_events(EventFilters(label="person"))
    assert {e.id for e in out} == {"1", "3"}


def test_filter_by_zone(monkeypatch):
    _patch_index(monkeypatch)
    out = events_service.search_events(EventFilters(zone="porch"))
    assert {e.id for e in out} == {"1"}


def test_views_carry_presigned_urls(monkeypatch):
    _patch_index(monkeypatch)
    out = events_service.search_events(EventFilters(camera="driveway"))
    assert out[0].clip_url is not None
    assert out[0].snapshot_url is not None


def test_invalid_date_raises(monkeypatch):
    _patch_index(monkeypatch)
    try:
        events_service.search_events(EventFilters(start_date="not-a-date"))
    except events_service.EventError as e:
        assert e.status_code == 400
    else:  # pragma: no cover
        raise AssertionError("expected EventError for bad date")
