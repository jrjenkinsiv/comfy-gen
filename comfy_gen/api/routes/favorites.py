"""Favorites API endpoints.

Mark generations as favorites, list favorites, and extract
reusable recipes from high-rated generations.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from comfy_gen.tracking.mlflow_tracker import MLFLOW_AVAILABLE, get_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/favorites", tags=["favorites"])


class MarkFavoriteRequest(BaseModel):
    """Request to mark a generation as favorite."""

    generation_id: str = Field(description="MLflow run ID to mark as favorite")
    rating: int = Field(default=5, ge=1, le=5, description="User rating 1-5")
    feedback: Optional[str] = Field(default=None, description="User feedback text")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")

    model_config = {"extra": "forbid"}


class FavoriteResponse(BaseModel):
    """Response for a favorite generation."""

    id: str
    generation_id: str
    recipe_hash: str
    rating: int
    feedback: Optional[str]
    image_url: Optional[str]
    categories: list[str]
    created_at: str


class ExtractRecipeRequest(BaseModel):
    """Request to extract a reusable recipe from a favorite."""

    target_categories: Optional[list[str]] = Field(
        default=None,
        description="Transfer recipe to different categories",
    )
    preserve_loras: bool = Field(default=True, description="Keep original LoRAs")
    preserve_settings: bool = Field(default=True, description="Keep steps/cfg/checkpoint")

    model_config = {"extra": "forbid"}


class RatingUpdate(BaseModel):
    """Request to update a generation's rating."""

    rating: int = Field(ge=1, le=5, description="New rating 1-5")
    feedback: Optional[str] = Field(default=None, description="Optional feedback")

    model_config = {"extra": "forbid"}


@router.post("", response_model=FavoriteResponse)
async def mark_favorite(request: MarkFavoriteRequest) -> FavoriteResponse:
    """Mark a generation as favorite.

    Updates MLflow run with favorite tag and rating.

    Args:
        request: MarkFavoriteRequest with generation_id and rating

    Returns:
        FavoriteResponse with updated info

    Raises:
        HTTPException 404: Generation not found
        HTTPException 503: MLflow unavailable
    """
    if not MLFLOW_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is not available",
        )

    tracker = get_tracker()
    if not tracker.enabled:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is disabled",
        )

    try:
        # Update existing run with favorite tag
        tracker.client.set_tag(request.generation_id, "favorite", "true")
        tracker.client.log_metric(
            request.generation_id,
            "user_rating",
            request.rating,
        )

        if request.feedback:
            tracker.client.set_tag(
                request.generation_id,
                "user_feedback",
                request.feedback[:500],
            )

        for tag in request.tags:
            tracker.client.set_tag(
                request.generation_id,
                f"user_tag_{tag}",
                "true",
            )

    except Exception as e:
        logger.error(f"Failed to mark favorite: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Generation not found: {e}",
        ) from e

    # Retrieve updated run
    try:
        run = tracker.client.get_run(request.generation_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to retrieve run: {e}",
        ) from e

    return FavoriteResponse(
        id=run.info.run_id,
        generation_id=request.generation_id,
        recipe_hash=run.data.tags.get("recipe_hash", ""),
        rating=request.rating,
        feedback=request.feedback,
        image_url=run.data.tags.get("image_url"),
        categories=run.data.tags.get("source_categories", "").split(","),
        created_at=str(run.info.start_time),
    )


@router.get("", response_model=list[FavoriteResponse])
async def list_favorites(
    min_rating: int = Query(4, ge=1, le=5, description="Minimum rating"),  # noqa: B008
    category: Optional[str] = Query(None, description="Filter by category"),  # noqa: B008
    limit: int = Query(20, ge=1, le=100, description="Max results"),  # noqa: B008
) -> list[FavoriteResponse]:
    """List favorite generations.

    Filters by minimum rating and optionally by category.

    Args:
        min_rating: Minimum user rating (default 4)
        category: Optional category filter
        limit: Maximum results to return

    Returns:
        List of FavoriteResponse objects
    """
    if not MLFLOW_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is not available",
        )

    tracker = get_tracker()
    if not tracker.enabled or not tracker.experiment_id:
        return []

    filter_parts = ['tags.favorite = "true"']
    filter_parts.append(f"metrics.user_rating >= {min_rating}")

    if category:
        filter_parts.append(f'tags.source_categories LIKE "%{category}%"')

    try:
        runs = tracker.client.search_runs(
            experiment_ids=[tracker.experiment_id],
            filter_string=" AND ".join(filter_parts),
            order_by=["metrics.user_rating DESC"],
            max_results=limit,
        )
    except Exception as e:
        logger.error(f"Failed to search favorites: {e}")
        return []

    return [
        FavoriteResponse(
            id=r.info.run_id,
            generation_id=r.info.run_id,
            recipe_hash=r.data.tags.get("recipe_hash", ""),
            rating=int(r.data.metrics.get("user_rating", 0)),
            feedback=r.data.tags.get("user_feedback"),
            image_url=r.data.tags.get("image_url"),
            categories=r.data.tags.get("source_categories", "").split(","),
            created_at=str(r.info.start_time),
        )
        for r in runs
    ]


@router.get("/{favorite_id}")
async def get_favorite(favorite_id: str) -> FavoriteResponse:
    """Get details for a specific favorite.

    Args:
        favorite_id: MLflow run ID

    Returns:
        FavoriteResponse with favorite details
    """
    if not MLFLOW_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is not available",
        )

    tracker = get_tracker()
    if not tracker.enabled:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is disabled",
        )

    try:
        run = tracker.client.get_run(favorite_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Favorite not found: {e}",
        ) from e

    return FavoriteResponse(
        id=run.info.run_id,
        generation_id=run.info.run_id,
        recipe_hash=run.data.tags.get("recipe_hash", ""),
        rating=int(run.data.metrics.get("user_rating", 0)),
        feedback=run.data.tags.get("user_feedback"),
        image_url=run.data.tags.get("image_url"),
        categories=run.data.tags.get("source_categories", "").split(","),
        created_at=str(run.info.start_time),
    )


@router.post("/{favorite_id}/extract-recipe")
async def extract_recipe(
    favorite_id: str,
    request: ExtractRecipeRequest,
) -> dict:
    """Extract a reusable recipe from a favorite.

    Optionally transfer recipe to new target categories.

    Args:
        favorite_id: MLflow run ID
        request: ExtractRecipeRequest with options

    Returns:
        Recipe dict
    """
    if not MLFLOW_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is not available",
        )

    tracker = get_tracker()
    if not tracker.enabled:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is disabled",
        )

    try:
        # Download recipe artifact
        artifact_path = tracker.client.download_artifacts(
            favorite_id,
            "recipe.json",
        )

        import json
        from pathlib import Path

        recipe_file = Path(artifact_path)
        if recipe_file.is_dir():
            recipe_file = recipe_file / "recipe.json"

        with recipe_file.open() as f:
            recipe_data = json.load(f)

    except Exception as e:
        logger.error(f"Failed to extract recipe: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Could not load recipe from favorite: {e}",
        ) from e

    # Transfer to new categories if requested
    if request.target_categories:
        from comfy_gen.composition.engine import CompositionEngine

        engine = CompositionEngine()

        try:
            new_recipe = engine.compose(request.target_categories)
            new_recipe_dict = new_recipe.model_dump()

            if request.preserve_loras:
                # Merge LoRAs from original
                new_recipe_dict["loras"].extend(recipe_data.get("loras", []))

            if request.preserve_settings:
                new_recipe_dict["steps"] = recipe_data.get("steps", new_recipe_dict["steps"])
                new_recipe_dict["cfg"] = recipe_data.get("cfg", new_recipe_dict["cfg"])
                new_recipe_dict["checkpoint"] = recipe_data.get("checkpoint")

            recipe_data = new_recipe_dict
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to transfer recipe: {e}",
            ) from e

    return recipe_data


@router.delete("/{favorite_id}")
async def remove_favorite(favorite_id: str) -> dict:
    """Remove favorite tag from a generation.

    Args:
        favorite_id: MLflow run ID

    Returns:
        Success message
    """
    if not MLFLOW_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is not available",
        )

    tracker = get_tracker()
    if not tracker.enabled:
        raise HTTPException(
            status_code=503,
            detail="MLflow tracking is disabled",
        )

    try:
        tracker.client.set_tag(favorite_id, "favorite", "false")
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Favorite not found: {e}",
        ) from e

    return {"message": "Favorite removed", "id": favorite_id}
