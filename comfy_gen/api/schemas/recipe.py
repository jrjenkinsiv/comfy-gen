"""Recipe schema - the deterministic, replayable generation configuration."""

from pydantic import BaseModel, Field


class LoRAConfig(BaseModel):
    """Configuration for a single LoRA."""

    filename: str = Field(description="LoRA filename")
    strength: float = Field(default=0.8, ge=0.0, le=2.0, description="LoRA strength")
    clip_strength: float | None = Field(default=None, ge=0.0, le=2.0, description="CLIP strength if different")

    model_config = {"json_schema_extra": {"example": {"filename": "add_detail.safetensors", "strength": 0.6}}}


class Recipe(BaseModel):
    """
    A deterministic, replayable generation recipe.

    This captures everything needed to reproduce a generation exactly.
    """

    # Source tracking
    source_categories: list[str] = Field(default_factory=list, description="Categories that contributed to this recipe")

    # Workflow
    workflow: str = Field(description="Workflow JSON filename")
    checkpoint: str | None = Field(default=None, description="Checkpoint model filename")

    # Prompts
    positive_prompt: str = Field(description="Final positive prompt")
    negative_prompt: str = Field(description="Final negative prompt")

    # LoRAs
    loras: list[LoRAConfig] = Field(default_factory=list, description="LoRA configurations")

    # Generation settings
    width: int = Field(default=1024, description="Output width")
    height: int = Field(default=1024, description="Output height")
    steps: int = Field(default=30, description="Sampling steps")
    cfg: float = Field(default=7.5, description="CFG scale")
    sampler: str = Field(default="euler", description="Sampler name")
    scheduler: str = Field(default="normal", description="Scheduler name")
    seed: int = Field(default=-1, description="Random seed")

    # Optional settings
    vae: str | None = Field(default=None, description="VAE model filename")
    clip_skip: int | None = Field(default=None, description="CLIP skip layers")
    denoise: float = Field(default=1.0, ge=0.0, le=1.0, description="Denoise strength for img2img")

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_categories": ["portrait", "outdoor"],
                "workflow": "flux-dev.json",
                "positive_prompt": "professional portrait, outdoor setting...",
                "negative_prompt": "blurry, bad quality...",
                "loras": [{"filename": "add_detail.safetensors", "strength": 0.6}],
                "width": 1024,
                "height": 1024,
                "steps": 30,
                "cfg": 7.5,
            }
        }
    }
