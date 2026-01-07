"""API route modules."""
from .generation import router as generation_router
from .health import router as health_router

__all__ = ["generation_router", "health_router"]
