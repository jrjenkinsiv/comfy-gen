"""Request/Response models for compose endpoint."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ComposeRequest(BaseModel):
    """Request to compose categories into a generation recipe."""

    input: str = Field(
        ...,
        description="User input with optional @tags and prompt text",
        examples=["@portrait @outdoor professional headshot natural lighting"],
    )
    dry_run: bool = Field(
        default=False,
        description="If true, returns recipe without executing generation",
    )
    max_categories: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of categories to include",
    )
    min_confidence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for inferred categories",
    )
    policy_tier: Literal["general", "mature", "explicit"] = Field(
        default="general",
        description="Content policy tier for access control",
    )

    model_config = {"extra": "forbid"}


class ExplanationStep(BaseModel):
    """Single step in the composition explanation."""

    phase: Literal["parsing", "classification", "composition", "validation"]
    action: str
    detail: str
    source: Optional[str] = None  # category ID or "system"


class ExplanationBlock(BaseModel):
    """Full explanation of how a recipe was composed.

    Enables transparency into the intelligent composition process.
    """

    summary: str = Field(description="Human-readable summary of composition")

    # Parsing phase
    explicit_tags: list[str] = Field(
        default_factory=list,
        description="@tags found in input",
    )
    inferred_categories: list[tuple[str, float]] = Field(
        default_factory=list,
        description="Categories inferred with (id, confidence)",
    )
    remaining_prompt: str = Field(
        default="",
        description="Prompt text after @tag extraction",
    )

    # Composition phase
    final_categories: list[str] = Field(
        default_factory=list,
        description="Final category IDs used in composition",
    )
    steps: list[ExplanationStep] = Field(
        default_factory=list,
        description="Detailed composition steps for provenance",
    )

    # Warnings and suggestions
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues during composition",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for improving results",
    )


class ComposeResponse(BaseModel):
    """Response from compose endpoint."""

    recipe: dict = Field(
        description="Composed generation recipe",
    )
    explanation: ExplanationBlock = Field(
        description="Explanation of how recipe was composed",
    )
    dry_run: bool = Field(
        description="Whether this was a dry run (no execution)",
    )
