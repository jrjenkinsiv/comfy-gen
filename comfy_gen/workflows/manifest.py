"""Workflow capability manifests.

Declares what each workflow file supports: LoRA slots, resolution ranges,
checkpoint types, etc. The composition engine uses manifests for
constraint satisfaction.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ResolutionConstraint(BaseModel):
    """Resolution constraints for a workflow."""

    min_width: int = Field(default=512, ge=64)
    max_width: int = Field(default=2048, le=8192)
    min_height: int = Field(default=512, ge=64)
    max_height: int = Field(default=2048, le=8192)
    prefer_square: bool = Field(default=False)
    aspect_ratios: list[str] = Field(default_factory=lambda: ["1:1", "4:3", "3:4", "16:9", "9:16"])

    model_config = {"extra": "forbid"}


class LoraConstraint(BaseModel):
    """LoRA constraints for a workflow."""

    max_loras: int = Field(default=5, ge=0, le=20)
    supports_clip_lora: bool = Field(default=False)
    supports_unet_lora: bool = Field(default=True)
    min_strength: float = Field(default=0.0, ge=0.0)
    max_strength: float = Field(default=2.0, le=5.0)

    model_config = {"extra": "forbid"}


class CheckpointConstraint(BaseModel):
    """Checkpoint constraints for a workflow."""

    required_type: Optional[Literal["sd15", "sdxl", "flux", "wan", "any"]] = Field(
        default=None,
        description="Required checkpoint type (e.g., 'sdxl', 'flux')",
    )
    compatible_checkpoints: list[str] = Field(
        default_factory=list,
        description="Specific checkpoint filenames this workflow supports",
    )
    requires_vae: bool = Field(default=False)

    model_config = {"extra": "forbid"}


class WorkflowManifest(BaseModel):
    """Capability manifest for a ComfyUI workflow.

    Describes what a workflow supports and its constraints.
    Used by the composition engine for constraint satisfaction.
    """

    # Identity
    workflow_file: str = Field(description="Workflow JSON filename")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(default="", description="Workflow description")

    # Capabilities
    supports_img2img: bool = Field(default=False)
    supports_inpainting: bool = Field(default=False)
    supports_controlnet: bool = Field(default=False)
    supports_video: bool = Field(default=False)
    supports_upscale: bool = Field(default=False)

    # Constraints
    resolution: ResolutionConstraint = Field(
        default_factory=ResolutionConstraint,
    )
    loras: LoraConstraint = Field(
        default_factory=LoraConstraint,
    )
    checkpoints: CheckpointConstraint = Field(
        default_factory=CheckpointConstraint,
    )

    # Node mapping for dynamic injection
    node_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Maps logical names to workflow node IDs (e.g., 'prompt': '6')",
    )

    # Generation defaults
    default_steps: int = Field(default=30, ge=1, le=150)
    default_cfg: float = Field(default=7.5, ge=1.0, le=30.0)
    default_sampler: str = Field(default="euler")
    default_scheduler: str = Field(default="normal")

    model_config = {"extra": "forbid"}

    def validate_lora_count(self, count: int) -> bool:
        """Check if LoRA count is within constraints."""
        return count <= self.loras.max_loras

    def validate_resolution(self, width: int, height: int) -> bool:
        """Check if resolution is within constraints."""
        return (
            self.resolution.min_width <= width <= self.resolution.max_width
            and self.resolution.min_height <= height <= self.resolution.max_height
        )

    def get_node_id(self, logical_name: str) -> Optional[str]:
        """Get workflow node ID for a logical name."""
        return self.node_mappings.get(logical_name)
