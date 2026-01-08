"""Generation endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from api.schemas import GenerationRequest, GenerationResponse, ProgressUpdate
from api.services.generation import get_generation_service

router = APIRouter()


@router.post("/generate", response_model=GenerationResponse, status_code=202)
async def create_generation(request: GenerationRequest) -> GenerationResponse:
    """Submit a new generation request.

    Args:
        request: Generation parameters

    Returns:
        GenerationResponse with job ID and initial status
    """
    service = get_generation_service()

    try:
        job_id = service.create_job(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            workflow=request.workflow,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg=request.cfg,
            seed=request.seed,
            loras=request.loras,
            sampler=request.sampler,
            scheduler=request.scheduler,
        )

        return GenerationResponse(
            id=job_id,
            status="queued",
            progress=0.0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create generation job: {str(e)}") from e


@router.get("/generate/{job_id}", response_model=GenerationResponse)
async def get_generation_status(job_id: str) -> GenerationResponse:
    """Get the status of a generation job.

    Args:
        job_id: Job ID to query

    Returns:
        GenerationResponse with current status

    Raises:
        HTTPException: If job not found
    """
    service = get_generation_service()
    job = service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return GenerationResponse(
        id=job.job_id,
        status=job.status,
        progress=job.progress,
        image_url=job.image_url,
        error=job.error,
    )


@router.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """Stream progress updates via WebSocket.

    Args:
        websocket: WebSocket connection
        job_id: Job ID to track

    Note:
        Sends ProgressUpdate messages as JSON at 1 second intervals
    """
    service = get_generation_service()

    # Check job exists
    job = service.get_job(job_id)
    if not job:
        await websocket.close(code=1008, reason=f"Job not found: {job_id}")
        return

    await websocket.accept()

    try:
        while True:
            # Get current job state
            job = service.get_job(job_id)
            if not job:
                break

            # Send progress update
            update = ProgressUpdate(
                job_id=job.job_id,
                status=job.status,
                progress=job.progress,
                step=job.current_step,
                max_steps=job.max_steps,
                image_url=job.image_url,
                error=job.error,
            )

            await websocket.send_json(update.model_dump())

            # If job is terminal, close connection
            if job.status in ["completed", "failed"]:
                break

            # Wait before next update (1 second interval)
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        # Close with error
        await websocket.close(code=1011, reason=str(e))
