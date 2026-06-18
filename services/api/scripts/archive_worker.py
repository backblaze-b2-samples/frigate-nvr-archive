#!/usr/bin/env python
"""Frigate -> B2 archive worker (CLI).

Polls a running Frigate instance for recently-ended detection events, downloads
each event's clip + snapshot, ships them to Backblaze B2 under the archive
prefix, and appends a searchable record to the day's JSONL index in B2.

Frigate is the detection engine — this worker never runs a model. It only
consumes Frigate's HTTP API via `app.repo.frigate_client`. B2 credentials are
the only secret required.

Usage (from services/api/, with .venv active and repo-root .env filled in):
    python scripts/archive_worker.py            # poll forever
    python scripts/archive_worker.py --once      # single pass, then exit
    python scripts/archive_worker.py --interval 15
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Make `app` importable when run as a standalone script from services/api/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(REPO_ROOT_ENV)

from app.config import settings  # noqa: E402
from app.service.archive import archive_recent  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("archive_worker")


def run_once() -> int:
    summary = archive_recent()
    logger.info(
        "Archive pass: scanned=%d archived=%d bytes=%d",
        summary["scanned"],
        summary["archived"],
        summary["bytes"],
    )
    return summary["archived"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Frigate -> B2 archive worker")
    parser.add_argument("--once", action="store_true", help="single pass then exit")
    parser.add_argument(
        "--interval",
        type=int,
        default=settings.archive_poll_interval_s,
        help="seconds between polls (loop mode)",
    )
    args = parser.parse_args()

    logger.info(
        "Starting archive worker: frigate=%s bucket=%s prefix=%s",
        settings.frigate_url,
        settings.b2_bucket_name,
        settings.archive_prefix,
    )

    if args.once:
        run_once()
        return

    while True:
        try:
            run_once()
        except RuntimeError as e:
            # Frigate or B2 hiccup — log and keep polling rather than crash.
            logger.error("Archive pass failed: %s", e)
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
