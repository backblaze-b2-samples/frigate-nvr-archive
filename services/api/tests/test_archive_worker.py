"""Unit tests for the Frigate -> B2 archive worker.

Frigate and B2 are both mocked at the repo boundary; the test asserts the worker
downloads each event's media, ships it to B2 under the archive prefix, and
appends a record to the JSONL index — without re-implementing detection.
"""

from app.config import settings
from app.service import archive as archive_service
from app.types import ArchiveEvent

RAW_EVENT = {
    "id": "1700000000.123-abc",
    "camera": "front_door",
    "label": "person",
    "top_score": 0.91,
    "zones": ["porch"],
    "start_time": 1700000000.0,
    "end_time": 1700000010.0,
}


def test_archive_event_ships_media_and_indexes(monkeypatch):
    puts: list[tuple[str, bytes]] = []
    appended: list[ArchiveEvent] = []

    monkeypatch.setattr(
        archive_service.frigate, "download_clip", lambda _id: b"CLIPDATA"
    )
    monkeypatch.setattr(
        archive_service.frigate, "download_snapshot", lambda _id: b"JPEG"
    )
    monkeypatch.setattr(
        archive_service.store,
        "put_bytes",
        lambda key, data, ct: (puts.append((key, data)) or len(data)),
    )
    monkeypatch.setattr(
        archive_service.store, "append_event", lambda e: appended.append(e)
    )
    monkeypatch.setattr(archive_service.store, "read_cameras", lambda: {})
    monkeypatch.setattr(archive_service.store, "write_cameras", lambda payload: None)

    event = archive_service.archive_event(RAW_EVENT)

    assert event is not None
    assert event.label == "person"
    assert event.camera == "front_door"
    assert event.zones == ["porch"]
    assert event.has_clip and event.has_snapshot
    # Both media objects land under the archive prefix on B2.
    keys = [k for k, _ in puts]
    assert all(k.startswith(settings.archive_prefix) for k in keys)
    assert any(k.endswith("/clip.mp4") for k in keys)
    assert any(k.endswith("/snapshot.jpg") for k in keys)
    # The event is recorded in the searchable index exactly once.
    assert len(appended) == 1
    assert appended[0].id == event.id


def test_archive_recent_skips_already_indexed(monkeypatch):
    existing = ArchiveEvent.model_validate(
        {
            "id": RAW_EVENT["id"],
            "camera": "front_door",
            "label": "person",
            "score": 0.9,
            "start_time": "2023-11-14T22:13:20+00:00",
            "archived_at": "2023-11-14T22:13:25+00:00",
        }
    )
    monkeypatch.setattr(
        archive_service.frigate, "list_events", lambda **kw: [RAW_EVENT]
    )
    monkeypatch.setattr(
        archive_service.store, "read_index_day", lambda day: [existing]
    )

    # archive_event must never be called because the id is already indexed.
    def _boom(_raw):  # pragma: no cover
        raise AssertionError("should not re-archive an existing event")

    monkeypatch.setattr(archive_service, "archive_event", _boom)

    summary = archive_service.archive_recent()
    assert summary["archived"] == 0
    assert summary["scanned"] == 1


def test_build_event_skips_malformed():
    assert archive_service._build_event({"id": None}) is None
