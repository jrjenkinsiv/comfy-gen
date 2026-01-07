"""Category schema - domain expertise with best practices."""
from enum import Enum

from pydantic import BaseModel, Field


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

    primary: list[str] = Field(default_factory=list, description="Primary keywords that strongly indicate this category")
    secondary: list[str] = Field(
        default_factory=list, description="Secondary keywords with weaker association"
    )


class Prompts(BaseModel):
    """Prompt fragments for this category."""

    positive: list[str] = Field(default_factory=list, description="Positive prompt fragments to inject")
    negative: list[str] = Field(default_factory=list, description="Negative prompt fragments to add")


class LoRADefaults(BaseModel):
    """Default LoRA configuration for a category."""

    filename: str = Field(description="LoRA filename")
    strength: float = Field(default=0.6, ge=0.0, le=2.0, description="Default strength")
    required: bool = Field(default=False, description="Whether this LoRA is required for the category")


class CategorySettings(BaseModel):
    """Optimized settings for a category."""

    steps: int | None = Field(default=None, description="Recommended steps")
    cfg: float | None = Field(default=None, description="Recommended CFG")
    sampler: str | None = Field(default=None, description="Recommended sampler")
    scheduler: str | None = Field(default=None, description="Recommended scheduler")
    width: int | None = Field(default=None, description="Recommended width")
    height: int | None = Field(default=None, description="Recommended height")


class CompositionRules(BaseModel):
    """Rules for composing this category with others."""

    stacks_with: list[str] = Field(default_factory=list, description="Categories this can combine with")
    conflicts_with: list[str] = Field(default_factory=list, description="Categories this conflicts with")
    priority: int = Field(default=50, ge=0, le=100, description="Priority when resolving conflicts (higher wins)")


class Category(BaseModel):
    """
    A category represents a domain of expertise with best practices.

    Categories capture what works well for specific subjects, settings, or styles.
    """

    # Identity
    id: str = Field(description="Unique category identifier (e.g., 'portrait', 'car', 'anime')")
    type: CategoryType = Field(description="Category type for composition rules")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(default="", description="Detailed description")

    # Content policy
    policy_tier: PolicyTier = Field(default=PolicyTier.GENERAL, description="Content policy tier")

    # Matching
    keywords: Keywords = Field(default_factory=Keywords, description="Keywords for NL matching")

    # Generation settings
    prompts: Prompts = Field(default_factory=Prompts, description="Prompt fragments")
    loras: list[LoRADefaults] = Field(default_factory=list, description="Recommended LoRAs")
    settings: CategorySettings = Field(default_factory=CategorySettings, description="Optimized settings")

    # Workflows
    workflows: list[str] = Field(default_factory=list, description="Compatible workflow files")

    # Composition
    composition: CompositionRules = Field(default_factory=CompositionRules, description="Composition rules")

    # Versioning
    schema_version: str = Field(default="1.0", description="Category schema version")

    model_config = {
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
                    "positive": ["professional portrait", "studio lighting"],
                    "negative": ["bad anatomy", "extra limbs"],
                },
            }
        }
    }
