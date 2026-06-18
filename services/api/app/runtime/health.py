from fastapi import APIRouter

from app.repo import check_connectivity
from app.repo import frigate_client as frigate

router = APIRouter()


@router.get("/health")
async def health():
    b2_ok = check_connectivity()
    frigate_ok = frigate.is_available()
    # B2 is the data store and is required; Frigate is the live ingest engine.
    # The app is still useful for browsing the existing archive if Frigate is
    # offline, so degraded reflects either dependency being down.
    return {
        "status": "healthy" if (b2_ok and frigate_ok) else "degraded",
        "b2_connected": b2_ok,
        "frigate_connected": frigate_ok,
    }
