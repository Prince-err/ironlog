"""Health check."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Service health")
def health():
    return {"status": "ok", "service": "iron-log-api"}
