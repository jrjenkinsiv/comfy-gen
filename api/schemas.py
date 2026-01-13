"""Pydantic schemas for API request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class GenerationRequest(BaseModel):
    """Request model for image generation."""

    prompt: str = Field(..., description="Positive text prompt")
    negative_prompt: str = Field(default="", description="Negative text prompt (what to avoid)")
    workflow: str = Field(default="flux-dev.json", description="Workflow JSON filename")
    width: int = Field(default=1024, ge=64, le=4096, description="Output width in pixels (divisible by 8)")
    height: int = Field(default=1024, ge=64, le=4096, description="Output height in pixels (divisible by 8)")
    steps: int = Field(default=20, ge=1, le=150, description="Number of sampling steps")
    cfg: float = Field(default=7.0, ge=1.0, le=20.0, description="Classifier-free guidance scale")
    seed: int = Field(default=-1, description="Random seed for reproducibility (-1 for random)")
    loras: list[str] = Field(default_factory=list, description="LoRA specifications (e.g., ['lora:0.8'])")
    sampler: Optional[str] = Field(default=None, description="Sampler algorithm")
    scheduler: Optional[str] = Field(default=None, description="Noise scheduler")

    @field_validator("width", "height")
    @classmethod
    def validate_divisible_by_8(cls, v: int, info) -> int:
        """Ensure dimensions are divisible by 8."""
        if v % 8 != 0:
            raise ValueError(f"{info.field_name} must be divisible by 8, got {v}")
        return v


class GenerationResponse(BaseModel):
    """Response model for generation status."""

    id: str = Field(..., description="Unique job ID")
    status: Literal["queued", "running", "completed", "failed"] = Field(..., description="Current job status")
    image_url: Optional[str] = Field(default=None, description="MinIO URL of generated image (when completed)")
    error: Optional[str] = Field(default=None, description="Error message (when failed)")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress percentage (0.0-1.0)")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Service status")
    comfyui_available: bool = Field(..., description="Whether ComfyUI server is reachable")
    version: str = Field(..., description="API version")


class ProgressUpdate(BaseModel):
    """WebSocket progress update message."""

    job_id: str = Field(..., description="Job ID being tracked")
    status: Literal["queued", "running", "completed", "failed"] = Field(..., description="Current status")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    step: Optional[int] = Field(default=None, description="Current sampling step")
    max_steps: Optional[int] = Field(default=None, description="Total sampling steps")
    message: Optional[str] = Field(default=None, description="Status message")
    image_url: Optional[str] = Field(default=None, description="Image URL when completed")
    error: Optional[str] = Field(default=None, description="Error message when failed")
