<!-- last_verified: 2026-06-18 -->
# Feature: Snapshot metadata extraction

## Purpose
Extract metadata from imported snapshots/clips and return it alongside upload
results — image dimensions and EXIF for snapshots, hashes/size for any media.

## Used By
- API: `POST /upload` (called after B2 upload)
- UI: upload results, file metadata panel

## Core Functions
- `services/api/app/service/metadata.py` — `extract_metadata()`, `_extract_image_metadata()`
- `apps/web/src/components/files/file-metadata-panel.tsx` — displays metadata in structured card

## Canonical Files
- Metadata extraction pattern: `services/api/app/service/metadata.py`
- Metadata display component: `apps/web/src/components/files/file-metadata-panel.tsx`

## Inputs
- file_data: bytes
- filename: string
- content_type: string

## Outputs
- `FileMetadataDetail`: filename, size_bytes, size_human, mime_type, extension, md5, sha256, uploaded_at
- Snapshot-specific (optional): image_width, image_height, exif dict
- (Other `FileMetadataDetail` fields exist for the shared type but are unused here)

## Flow
- Upload route receives the clip/snapshot and stores it in B2
- `extract_metadata()` called with file bytes, filename, content type
- Computes MD5 and SHA-256 hashes
- If image (snapshot): opens with Pillow, extracts dimensions and EXIF data
- Returns `FileMetadataDetail` model
- Frontend displays metadata in file-metadata-panel component

## Edge Cases
- Corrupt image → Pillow fails silently, image fields remain null
- Non-image media (clips) → only common fields populated (hashes, size, extension)
- EXIF contains binary data → decoded as UTF-8 with replace, converted to string
- Large file → hashing may be slow (computed in-memory)

## UX States
- Not applicable (metadata is part of upload response and file preview)

## Verification
- Test files: `services/api/tests/` (no dedicated metadata tests yet)
- Required cases: snapshot with EXIF, snapshot without EXIF, clip (non-image), corrupt image handling
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Upload](file-upload.md)
