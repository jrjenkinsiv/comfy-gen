"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import generation_router

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
