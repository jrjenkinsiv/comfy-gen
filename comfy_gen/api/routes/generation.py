"""Generation API routes - POST /generate, GET /generate/{id}."""

import logging
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ...services.generation import ComfyUIExecutor, GenerationPipeline
from ..schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    ProgressInfo,
)

router = APIRouter(prefix="/api/v1", tags=["generation"])
logger = logging.getLogger(__name__)

# In-memory generation store (will be replaced with Redis for production)
generation_store: dict[str, dict] = {}

# Service instances (will be injected via dependency injection in production)
executor = ComfyUIExecutor(server_address="192.168.1.215:8188")
pipeline = GenerationPipeline(executor=executor, workflows_dir="workflows")


async def execute_generation(generation_id: str, request: GenerationRequest) -> None:
    """
    Background task that executes the actual generation via ComfyUI.
    """
    logger.info(f"Starting generation {generation_id}")
    generation_store[generation_id]["status"] = GenerationStatus.RUNNING

    try:
        # Check if ComfyUI is reachable
        if not await executor.check_health():
            raise RuntimeError("ComfyUI server not reachable")

        # Update progress as queued
        generation_store[generation_id]["progress"] = ProgressInfo(
            current_step=0,
            total_steps=request.steps,
            percent=0.0,
            current_node="queuing",
        )

        # Execute via pipeline
        result = await pipeline.execute(request, client_id=generation_id)

        # Mark as completed
        generation_store[generation_id]["status"] = GenerationStatus.COMPLETED
        generation_store[generation_id]["image_url"] = result.image_url
        generation_store[generation_id]["generation_time"] = result.execution_time
        generation_store[generation_id]["progress"] = ProgressInfo(
            current_step=request.steps,
            total_steps=request.steps,
            percent=1.0,
        )
        logger.info(f"Generation {generation_id} completed in {result.execution_time:.2f}s")

    except Exception as e:
        logger.error(f"Generation {generation_id} failed: {e}")
        generation_store[generation_id]["status"] = GenerationStatus.FAILED
        generation_store[generation_id]["error"] = str(e)


@router.post("/generate", response_model=GenerationResponse)
async def create_generation(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
) -> GenerationResponse:
    """
    Queue a new image generation.

    Returns immediately with a generation_id. Poll GET /api/v1/generate/{id}
    for status updates, or connect to WebSocket for real-time progress.
    """
    generation_id = str(uuid4())

    # Initialize generation state
    generation_store[generation_id] = {
        "status": GenerationStatus.QUEUED,
        "request": request.model_dump(),
        "progress": None,
        "image_url": None,
        "error": None,
        "categories_used": request.categories or [],
        "generation_time": None,
    }

    # Queue background execution
    background_tasks.add_task(execute_generation, generation_id, request)

    logger.info(f"Queued generation {generation_id}: prompt='{request.prompt[:50]}...'")

    return GenerationResponse(
        generation_id=generation_id,
        status=GenerationStatus.QUEUED,
        message="Generation queued. Poll GET /api/v1/generate/{id} for status.",
    )


@router.get("/generate/{generation_id}", response_model=GenerationResponse)
async def get_generation_status(generation_id: str) -> GenerationResponse:
    """
    Get the status of a generation request.

    Poll this endpoint to track progress and retrieve results.
    """
    if generation_id not in generation_store:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")

    data = generation_store[generation_id]

    return GenerationResponse(
        generation_id=generation_id,
        status=data["status"],
        message=data.get("error"),
        progress=data.get("progress"),
        image_url=data.get("image_url"),
        categories_used=data.get("categories_used"),
        generation_time=data.get("generation_time"),
    )


@router.delete("/generate/{generation_id}")
async def cancel_generation(generation_id: str) -> dict:
    """
    Cancel a queued or running generation.

    Note: May not stop an already-running ComfyUI generation immediately.
    """
    if generation_id not in generation_store:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")

    # Remove from store (background task will detect this)
    del generation_store[generation_id]

    logger.info(f"Cancelled generation {generation_id}")

    return {"status": "cancelled", "generation_id": generation_id}
