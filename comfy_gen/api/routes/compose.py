"""Compose endpoint - intelligent category composition.

The /compose endpoint is the primary intelligent composition API.
It parses user input, selects categories, composes a recipe,
and returns an explainable result with ExplanationBlock.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from comfy_gen.api.schemas.compose import (
    ComposeRequest,
    ComposeResponse,
    ExplanationBlock,
    ExplanationStep,
)
from comfy_gen.categories.registry import CategoryRegistry
from comfy_gen.composition.engine import CompositionEngine, CompositionError
from comfy_gen.parsing.intent_classifier import HybridParser
from comfy_gen.policy.content_policy import check_policy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compose", tags=["compose"])


@router.post("", response_model=ComposeResponse)
async def compose_recipe(request: ComposeRequest) -> ComposeResponse:
    """Compose categories into a generation recipe.

    Parses user input for @tags and keywords, selects categories,
    validates against policy tier, and returns a composed recipe
    with full explanation.

    Args:
        request: ComposeRequest with input text and options

    Returns:
        ComposeResponse with recipe and explanation

    Raises:
        HTTPException 400: No categories matched
        HTTPException 403: Policy tier violation
    """
    registry = CategoryRegistry.get_instance()
    parser = HybridParser(registry, min_confidence=request.min_confidence)
    engine = CompositionEngine(registry)

    steps: list[ExplanationStep] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    # Phase 1: Parse input
    logger.debug(f"Parsing input: {request.input[:100]}...")
    parse_result = parser.parse(request.input)

    steps.append(
        ExplanationStep(
            phase="parsing",
            action="extract_tags",
            detail=f"Found {len(parse_result['explicit_categories'])} explicit @tags",
            source="system",
        )
    )

    if parse_result["unmatched_tags"]:
        warnings.append(f"Unknown tags ignored: {parse_result['unmatched_tags']}")
        suggestions.append("Use /api/v1/categories to see available category IDs")

    steps.append(
        ExplanationStep(
            phase="classification",
            action="infer_categories",
            detail=f"Inferred {len(parse_result['inferred_categories'])} categories from keywords",
            source="system",
        )
    )

    # Phase 2: Select final categories
    category_ids = parse_result["explicit_categories"].copy()

    # Add inferred categories up to max
    for cat_id, confidence in parse_result["inferred_categories"]:
        if len(category_ids) >= request.max_categories:
            break
        if cat_id not in category_ids:
            category_ids.append(cat_id)
            steps.append(
                ExplanationStep(
                    phase="classification",
                    action="add_inferred",
                    detail=f"Added {cat_id} (confidence: {confidence:.2f})",
                    source=cat_id,
                )
            )

    if not category_ids:
        raise HTTPException(
            status_code=400,
            detail="No categories matched. Use @tags or keywords that match category definitions.",
        )

    # Phase 3: Policy tier check
    categories = [registry.get(cid) for cid in category_ids if registry.get(cid)]

    from comfy_gen.api.schemas.category import PolicyTier

    policy_result = check_policy(categories, PolicyTier(request.policy_tier))

    if not policy_result.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "policy_violation",
                "message": "One or more categories require elevated policy tier",
                "violations": policy_result.violation_messages,
            },
        )

    steps.append(
        ExplanationStep(
            phase="validation",
            action="policy_check",
            detail=f"Policy tier {request.policy_tier} validated",
            source="system",
        )
    )

    # Phase 4: Compose recipe
    try:
        recipe = engine.compose(category_ids)
    except CompositionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Add composition steps to explanation
    for comp_step in recipe.composition_steps:
        steps.append(
            ExplanationStep(
                phase="composition",
                action=comp_step.action,
                detail=comp_step.detail,
                source=comp_step.source,
            )
        )

    warnings.extend(recipe.warnings)

    # Build summary
    summary = _build_summary(category_ids, recipe, parse_result)

    explanation = ExplanationBlock(
        summary=summary,
        explicit_tags=parse_result["explicit_categories"],
        inferred_categories=parse_result["inferred_categories"],
        remaining_prompt=parse_result["remaining_prompt"],
        final_categories=category_ids,
        steps=steps,
        warnings=warnings,
        suggestions=suggestions,
    )

    logger.info(f"Composed recipe with {len(category_ids)} categories: {category_ids}")

    return ComposeResponse(
        recipe=recipe.model_dump(),
        explanation=explanation,
        dry_run=request.dry_run,
    )


def _build_summary(
    category_ids: list[str],
    recipe,
    parse_result: dict,
) -> str:
    """Build human-readable summary of composition.

    Args:
        category_ids: Final category IDs
        recipe: Composed Recipe
        parse_result: Result from hybrid parser

    Returns:
        Human-readable summary string
    """
    parts = []

    if parse_result["explicit_categories"]:
        count = len(parse_result["explicit_categories"])
        parts.append(f"Using {count} explicit {'category' if count == 1 else 'categories'}")

    if parse_result["inferred_categories"]:
        count = len(parse_result["inferred_categories"])
        parts.append(f"{count} inferred from keywords")

    parts.append(f"Composed recipe with {len(recipe.loras)} LoRAs")
    parts.append(f"workflow: {recipe.workflow}")

    return ". ".join(parts) + "."


@router.post("/preview")
async def preview_composition(request: ComposeRequest) -> dict:
    """Preview composition without full recipe generation.

    Lighter-weight endpoint that shows what categories would be matched
    without running the full composition engine.

    Args:
        request: ComposeRequest

    Returns:
        Dict with parsing results and category matches
    """
    registry = CategoryRegistry.get_instance()
    parser = HybridParser(registry, min_confidence=request.min_confidence)

    parse_result = parser.parse(request.input)

    # Get category details
    explicit_details = []
    for cat_id in parse_result["explicit_categories"]:
        cat = registry.get(cat_id)
        if cat:
            explicit_details.append(
                {
                    "id": cat.id,
                    "display_name": cat.display_name,
                    "type": cat.type.value,
                    "policy_tier": cat.policy_tier.value,
                }
            )

    inferred_details = []
    for cat_id, confidence in parse_result["inferred_categories"]:
        cat = registry.get(cat_id)
        if cat:
            inferred_details.append(
                {
                    "id": cat.id,
                    "display_name": cat.display_name,
                    "type": cat.type.value,
                    "confidence": confidence,
                }
            )

    return {
        "explicit_categories": explicit_details,
        "inferred_categories": inferred_details,
        "unmatched_tags": parse_result["unmatched_tags"],
        "remaining_prompt": parse_result["remaining_prompt"],
        "total_categories": len(explicit_details) + len(inferred_details),
    }
