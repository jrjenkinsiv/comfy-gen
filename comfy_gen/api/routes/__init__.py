"""API route modules."""

from .categories import router as categories_router
from .generation import router as generation_router
from .health import router as health_router

__all__ = ["categories_router", "generation_router", "health_router"]
