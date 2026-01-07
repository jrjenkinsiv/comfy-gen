"""Category schema - domain expertise with best practices.

This module defines Pydantic models that align with the JSON Schema at
comfy_gen/categories/schema.json for category YAML validation.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


class CategoryType(str, Enum):
    """Type of category for composition rules."""

    SUBJECT = "subject"  # Main focus (car, person, animal)
    SETTING = "setting"  # Where it takes place (city, beach, forest)
    MODIFIER = "modifier"  # Atmospheric (night, rainy, golden-hour)
    STYLE = "style"  # Rendering style (anime, photorealistic)


class PolicyTier(str, Enum):
    """Content policy tier for access control."""

    GENERAL = "general"  # Safe for all audiences
    MATURE = "mature"  # Adult themes, suggestive
    EXPLICIT = "explicit"  # NSFW content


class Keywords(BaseModel):
    """Keywords for category matching."""

    primary: list[str] = Field(
        ...,  # Required field
        min_length=1,
        description="Primary keywords that strongly indicate this category",
    )
    secondary: list[str] = Field(default_factory=list, description="Secondary keywords with weaker association")
    specific: list[str] = Field(default_factory=list, description="Specific/rare keywords for exact matching")

    model_config = {"extra": "forbid"}


class PromptFragments(BaseModel):
    """Prompt fragment lists for required/optional injection."""

    required: list[str] = Field(default_factory=list, description="Always included in prompt")
    optional: list[str] = Field(default_factory=list, description="Included if compatible")

    model_config = {"extra": "forbid"}


class Prompts(BaseModel):
    """Prompt fragments for this category."""

    positive_fragments: PromptFragments = Field(
        default_factory=PromptFragments, description="Positive prompt fragments to inject"
    )
    negative_fragments: PromptFragments = Field(
        default_factory=PromptFragments, description="Negative prompt fragments to add"
    )

    model_config = {"extra": "forbid"}


class LoraConfig(BaseModel):
    """LoRA configuration with strength and trigger words."""

    filename: str = Field(..., description="LoRA filename (with .safetensors)")
    strength: float = Field(default=0.8, ge=0.0, le=2.0, description="LoRA strength (0.0-2.0)")
    trigger_words: list[str] = Field(default_factory=list, description="Keywords to add when using this LoRA")
    condition: Optional[str] = Field(default=None, description="When to use (e.g., 'if nsfw', 'if photorealistic')")

    model_config = {"extra": "forbid"}


class LoraSettings(BaseModel):
    """LoRA recommendations for a category."""

    required: list[LoraConfig] = Field(default_factory=list, description="LoRAs that must be used")
    recommended: list[LoraConfig] = Field(default_factory=list, description="LoRAs that improve quality")
    avoid: list[str] = Field(default_factory=list, description="LoRA filenames to avoid (conflicts)")

    model_config = {"extra": "forbid"}


class RangeConfig(BaseModel):
    """Min/max/default range configuration."""

    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    default: Optional[Union[int, float]] = None

    model_config = {"extra": "forbid"}


class SizeConfig(BaseModel):
    """Image size configuration."""

    width: Optional[int] = Field(default=None, ge=64, le=4096)
    height: Optional[int] = Field(default=None, ge=64, le=4096)
    aspect_ratio: Optional[str] = Field(default=None, pattern=r"^\d+:\d+$", description="Aspect ratio like '16:9'")

    model_config = {"extra": "forbid"}


class GenerationSettings(BaseModel):
    """Generation parameter overrides for a category."""

    steps: Optional[RangeConfig] = None
    cfg: Optional[RangeConfig] = None
    size: Optional[SizeConfig] = None
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    denoise: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    model_config = {"extra": "forbid"}


class WorkflowConfig(BaseModel):
    """Workflow preferences for a category."""

    preferred: list[str] = Field(default_factory=list, description="Preferred workflow files (in order)")
    required_capabilities: list[str] = Field(default_factory=list, description="Capabilities workflow must have")
    excluded: list[str] = Field(default_factory=list, description="Workflows to never use")

    model_config = {"extra": "forbid"}


class CompositionRules(BaseModel):
    """Rules for combining this category with others."""

    priority: int = Field(default=50, ge=0, le=100, description="Priority when resolving conflicts (higher wins)")
    conflicts_with: list[str] = Field(default_factory=list, description="Category IDs that conflict")
    requires: list[str] = Field(default_factory=list, description="Category IDs that must also be present")
    enhances: list[str] = Field(default_factory=list, description="Category IDs this enhances (synergy)")
    max_per_type: Optional[int] = Field(default=None, ge=1, description="Max categories of same type to combine")

    model_config = {"extra": "forbid"}


class Category(BaseModel):
    """
    A category represents a domain of expertise with best practices.

    Categories capture what works well for specific subjects, settings, or styles.
    This model aligns with comfy_gen/categories/schema.json (JSON Schema Draft-07).
    """

    # Identity (required fields)
    id: str = Field(..., description="Unique category identifier (lowercase, underscores allowed)")
    type: CategoryType = Field(..., description="Category type for composition rules")
    display_name: str = Field(..., description="Human-readable name for UI")

    # Optional identity fields
    description: str = Field(default="", description="Detailed description of this category")
    icon: str = Field(default="", description="Emoji or icon identifier for UI")

    # Versioning
    schema_version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Schema version this category adheres to",
    )

    # Content policy
    policy_tier: PolicyTier = Field(default=PolicyTier.GENERAL, description="Content policy tier")

    # Matching (required)
    keywords: Keywords = Field(..., description="Keywords for NL matching")

    # Generation settings (optional)
    prompts: Prompts = Field(default_factory=Prompts, description="Prompt fragments")
    loras: LoraSettings = Field(default_factory=LoraSettings, description="LoRA recommendations")
    settings: GenerationSettings = Field(
        default_factory=GenerationSettings, description="Generation parameter overrides"
    )

    # Workflows (optional)
    workflows: Optional[WorkflowConfig] = Field(default=None, description="Workflow preferences")

    # Composition rules (optional)
    composition: CompositionRules = Field(
        default_factory=CompositionRules, description="Rules for combining with other categories"
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate that ID is lowercase letters, numbers, and underscores only."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "Category ID must start with lowercase letter and contain only "
                "lowercase letters, numbers, and underscores"
            )
        return v

    model_config = {
        "extra": "forbid",  # Catch typos in YAML
        "json_schema_extra": {
            "example": {
                "id": "portrait",
                "type": "subject",
                "display_name": "Portrait Photography",
                "description": "Human portraits and headshots",
                "policy_tier": "general",
                "keywords": {
                    "primary": ["portrait", "face", "person", "headshot"],
                    "secondary": ["closeup", "profile"],
                },
                "prompts": {
                    "positive_fragments": {
                        "required": ["professional portrait", "studio lighting"],
                    },
                    "negative_fragments": {
                        "required": ["bad anatomy", "extra limbs"],
                    },
                },
            }
        },
    }


class CategoryWrapper(BaseModel):
    """Wrapper model matching the YAML file structure."""

    category: Category

    model_config = {"extra": "forbid"}
