"""Recipe model - composed generation parameters.

A Recipe is the output of the composition engine, containing all
parameters needed to generate an image from multiple categories.
"""

from __future__ import annotations

import hashlib
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CompositionStep(BaseModel):
    """Single step in the composition process for provenance tracking."""

    action: Literal[
        "add_category",
        "merge_prompts",
        "stack_lora",
        "resolve_conflict",
        "apply_settings",
        "select_workflow",
    ]
    source: str = Field(description="Category ID or 'system'")
    detail: str = Field(description="Human-readable description of this step")


class LoraStack(BaseModel):
    """Resolved LoRA configuration from composition."""

    filename: str = Field(description="LoRA filename")
    strength: float = Field(default=0.8, ge=0.0, le=2.0, description="LoRA strength")
    source_categories: list[str] = Field(default_factory=list, description="Categories that requested this LoRA")
    trigger_words: list[str] = Field(default_factory=list, description="Combined trigger words from all sources")


class Recipe(BaseModel):
    """Composed generation recipe from multiple categories.

    A Recipe contains all parameters needed to generate an image,
    along with provenance information about how it was composed.
    """

    # Identity
    id: str = Field(description="Unique recipe ID (hash of category inputs)")
    source_categories: list[str] = Field(description="Category IDs that composed this recipe")

    # Merged prompts
    positive_prompt: str = Field(description="Merged positive prompt")
    negative_prompt: str = Field(default="", description="Merged negative prompt")

    # LoRA stack
    loras: list[LoraStack] = Field(default_factory=list, description="Stacked LoRA configurations")

    # Generation settings
    steps: int = Field(default=30, ge=1, le=150)
    cfg: float = Field(default=7.5, ge=1.0, le=30.0)
    width: int = Field(default=1024, ge=64, le=4096)
    height: int = Field(default=1024, ge=64, le=4096)
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    denoise: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    checkpoint: Optional[str] = None
    vae: Optional[str] = None

    # Workflow
    workflow: str = Field(default="flux-dev.json", description="Selected workflow file")

    # Provenance
    composition_steps: list[CompositionStep] = Field(default_factory=list, description="Steps taken during composition")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal issues during composition")

    @staticmethod
    def generate_id(category_ids: list[str]) -> str:
        """Generate deterministic recipe ID from category IDs.

        Args:
            category_ids: List of category IDs

        Returns:
            16-character hex string
        """
        content = ":".join(sorted(category_ids))
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_lora_string(self) -> str:
        """Get LoRA stack as a comma-separated string.

        Returns:
            String like "lora1:0.8,lora2:0.6"
        """
        return ",".join(f"{l.filename}:{l.strength}" for l in self.loras)

    def get_trigger_words(self) -> list[str]:
        """Get all trigger words from LoRA stack.

        Returns:
            Deduplicated list of trigger words
        """
        seen = set()
        result = []
        for lora in self.loras:
            for tw in lora.trigger_words:
                if tw.lower() not in seen:
                    seen.add(tw.lower())
                    result.append(tw)
        return result

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "a1b2c3d4e5f67890",
                "source_categories": ["portrait", "night"],
                "positive_prompt": "professional portrait, studio lighting, nighttime, dark atmosphere",
                "negative_prompt": "bad anatomy, extra limbs",
                "loras": [
                    {
                        "filename": "add_detail.safetensors",
                        "strength": 0.5,
                        "source_categories": ["portrait"],
                        "trigger_words": [],
                    }
                ],
                "steps": 40,
                "cfg": 8.0,
                "width": 1024,
                "height": 1024,
                "workflow": "flux-dev.json",
            }
        }
    }
