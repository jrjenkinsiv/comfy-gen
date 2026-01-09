"""Health check endpoint."""

from fastapi import APIRouter

from api import __version__
from api.schemas import HealthResponse
from clients.comfyui_client import ComfyUIClient

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health and ComfyUI availability.

    Returns:
        HealthResponse with service status and ComfyUI availability
    """
    client = ComfyUIClient()
    comfyui_available = client.check_availability()

    return HealthResponse(
        status="healthy" if comfyui_available else "degraded",
        comfyui_available=comfyui_available,
        version=__version__,
    )
