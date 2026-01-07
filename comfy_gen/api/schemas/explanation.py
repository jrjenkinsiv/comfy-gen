"""Explanation schema - justification tree for composition decisions."""

from typing import Optional, Union

from pydantic import BaseModel, Field


class CategoryMatch(BaseModel):
    """Record of how a category was matched."""

    id: str = Field(description="Category ID that matched")
    matched_by: list[str] = Field(description="Keywords or @tags that triggered the match")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Match confidence score")
    source: str = Field(default="keyword", description="Match source: 'tag', 'keyword', 'llm'")


class ConflictResolution(BaseModel):
    """Record of how a conflict was resolved."""

    categories: list[str] = Field(description="Categories involved in the conflict")
    conflict_type: str = Field(description="Type: 'semantic', 'style', 'subject', 'exclusive'")
    resolution: str = Field(description="How it was resolved")
    winner: Optional[str] = Field(default=None, description="Which category won (if applicable)")


class LoRASelection(BaseModel):
    """Record of why a LoRA was selected."""

    filename: str = Field(description="LoRA filename")
    strength: float = Field(description="Applied strength")
    reason: str = Field(description="Why this LoRA was selected")
    category_source: str = Field(description="Which category recommended it")


class WorkflowSelection(BaseModel):
    """Record of why a workflow was chosen."""

    chosen: str = Field(description="Workflow filename that was selected")
    reason: str = Field(description="Why this workflow was chosen")
    alternatives_considered: list[str] = Field(default_factory=list, description="Other workflows that were considered")
    constraints_satisfied: list[str] = Field(default_factory=list, description="Requirements this workflow meets")


class ParameterDecision(BaseModel):
    """Record of how a parameter value was determined."""

    parameter: str = Field(description="Parameter name (e.g., 'steps', 'cfg')")
    value: Union[int, float, str] = Field(description="Final value")
    source: str = Field(description="Where the value came from: 'category', 'default', 'user', 'merged')")
    reasoning: Optional[str] = Field(default=None, description="Additional reasoning if complex")


class ExplanationBlock(BaseModel):
    """
    Justification tree for all composition decisions.

    Every generation produces both a Recipe (what) and an ExplanationBlock (why).
    This enables debugging, learning, and transparency.
    """

    # Summary
    summary: str = Field(description="One-sentence summary of what was composed")

    # Category matching
    explicit_tags: list[str] = Field(default_factory=list, description="@tags explicitly specified by user")
    inferred_categories: list[CategoryMatch] = Field(
        default_factory=list, description="Categories inferred from natural language"
    )
    final_categories: list[str] = Field(description="Final list of category IDs used")

    # Conflict resolution
    conflict_resolutions: list[ConflictResolution] = Field(
        default_factory=list, description="How conflicts were resolved"
    )

    # Prompt construction
    prompt_ordering_rationale: str = Field(description="Why prompt elements are ordered as they are")

    # LoRA selection
    lora_selection: list[LoRASelection] = Field(default_factory=list, description="Why each LoRA was chosen")
    lora_caps_applied: bool = Field(default=False, description="Whether LoRA count was capped")
    lora_cap_reason: Optional[str] = Field(default=None, description="Reason for cap if applied")

    # Workflow selection
    workflow_selection: WorkflowSelection = Field(description="Why this workflow was chosen")

    # Parameter decisions
    parameter_decisions: list[ParameterDecision] = Field(
        default_factory=list, description="How each parameter was determined"
    )

    # Settings source map
    settings_source: dict[str, str] = Field(default_factory=dict, description="Map of parameter -> source category")

    # Warnings
    warnings: list[str] = Field(default_factory=list, description="Any warnings during composition")

    model_config = {
        "json_schema_extra": {
            "example": {
                "summary": "Portrait in outdoor setting with golden hour lighting",
                "explicit_tags": ["portrait"],
                "inferred_categories": [{"id": "outdoor", "matched_by": ["garden", "sunlight"], "confidence": 0.85}],
                "final_categories": ["portrait", "outdoor", "golden-hour"],
                "prompt_ordering_rationale": "Subject first, then setting, then modifiers",
                "workflow_selection": {
                    "chosen": "flux-dev.json",
                    "reason": "Best for photorealistic portraits",
                    "constraints_satisfied": ["portrait_compatible", "high_quality"],
                },
                "warnings": [],
            }
        }
    }
