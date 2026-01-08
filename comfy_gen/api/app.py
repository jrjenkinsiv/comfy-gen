"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes import (
    categories_router,
    compose_router,
    favorites_router,
    generation_router,
)
from .websocket import websocket_progress_endpoint

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("ComfyGen API starting up...")
    logger.info(f"ComfyUI server: {settings.comfyui_url}")
    logger.info(f"MinIO endpoint: {settings.MINIO_ENDPOINT}")
    logger.info(f"MLflow tracking: {settings.MLFLOW_TRACKING_URI}")

    # Initialize category registry
    from comfy_gen.categories.registry import CategoryRegistry

    registry = CategoryRegistry.get_instance()
    logger.info(f"Loaded {len(registry)} categories")

    yield
    # Shutdown
    logger.info("ComfyGen API shutting down...")


app = FastAPI(
    title="ComfyGen API",
    description="Intelligent image generation API powered by ComfyUI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(generation_router)
app.include_router(categories_router, prefix="/api/v1")
app.include_router(compose_router, prefix="/api/v1")
app.include_router(favorites_router, prefix="/api/v1")

# Mount GUI static files
gui_static_path = Path(__file__).parent.parent / "gui" / "static"
if gui_static_path.exists():
    app.mount("/static", StaticFiles(directory=str(gui_static_path)), name="static")
    logger.info(f"Mounted GUI static files from {gui_static_path}")

# Setup GUI routes (Jinja2 templates)
try:
    from comfy_gen.gui import setup_gui

    setup_gui(app)
    logger.info("GUI routes configured")
except ImportError as e:
    logger.warning(f"GUI not available: {e}")


# Health check endpoint
@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns basic service health status.
    """
    return {
        "status": "healthy",
        "service": "comfy-gen-api",
        "version": "0.1.0",
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint with API info."""
    return {
        "service": "ComfyGen API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# WebSocket endpoint for real-time progress
@app.websocket("/ws/progress/{generation_id}")
async def websocket_progress(websocket: WebSocket, generation_id: str):
    """
    WebSocket endpoint for real-time generation progress.

    Connect to receive progress updates for a specific generation.
    Messages:
    - {"type": "progress", "value": 15, "max": 50, "step": "Step 15 of 50"}
    - {"type": "executing", "node": "KSampler", "message": "..."}
    - {"type": "complete", "image_url": "..."}
    - {"type": "error", "message": "..."}
    """
    await websocket_progress_endpoint(websocket, generation_id)


def create_app() -> FastAPI:
    """Factory function for creating the FastAPI app."""
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "comfy_gen.api.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
