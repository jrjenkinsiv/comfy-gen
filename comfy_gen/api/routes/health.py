"""Health check routes."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "comfy-gen-api",
        "version": "0.1.0",
    }
