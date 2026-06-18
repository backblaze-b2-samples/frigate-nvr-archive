"""Unit tests for clip-import filename handling.

Upload here imports an external clip/snapshot into the archive prefix on B2.
"""

from app.config import settings
from app.service import upload as upload_service
from app.types import FileUploadResponse


def _fake_upload(file_data, key, content_type):
    return FileUploadResponse(
        key=key,
        filename="clip.mp4",
        size_bytes=len(file_data),
        size_human="5 B",
        content_type=content_type,
        uploaded_at="2026-02-14T00:00:00Z",
        url=None,
        metadata=None,
    )


def test_upload_allows_duplicate_filename(monkeypatch):
    """B2 is always versioned — re-uploading the same name creates a new version."""
    monkeypatch.setattr(upload_service, "upload_file", _fake_upload)
    monkeypatch.setattr(upload_service, "extract_metadata", lambda *a, **k: None)

    result = upload_service.process_upload(
        file_data=b"hello",
        filename="clip.mp4",
        content_type="video/mp4",
        content_length=5,
    )

    assert result.key == f"{settings.archive_prefix}imports/clip.mp4"


def test_upload_rejects_disallowed_type(monkeypatch):
    """Only surveillance media (clips/snapshots) may be imported."""
    monkeypatch.setattr(upload_service, "upload_file", _fake_upload)
    monkeypatch.setattr(upload_service, "extract_metadata", lambda *a, **k: None)

    try:
        upload_service.process_upload(
            file_data=b"hello",
            filename="notes.txt",
            content_type="text/plain",
            content_length=5,
        )
    except upload_service.UploadError as e:
        assert e.status_code == 415
    else:  # pragma: no cover
        raise AssertionError("expected UploadError for text/plain")
