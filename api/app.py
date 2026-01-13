"""FastAPI application for ComfyGen generation server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.routes import generate, health

# Create FastAPI app
app = FastAPI(
    title="ComfyGen Generation API",
    description="FastAPI server for programmatic image generation using ComfyUI",
    version=__version__,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(generate.router, tags=["generation"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ComfyGen API",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
