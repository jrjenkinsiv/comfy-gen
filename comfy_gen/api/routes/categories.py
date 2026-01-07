"""Category API endpoints.

Provides REST API for browsing and searching categories.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from comfy_gen.api.schemas.category import Category, CategoryType
from comfy_gen.categories.registry import CategoryRegistry

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryListResponse(BaseModel):
    """Paginated category list response."""

    items: list[Category] = Field(description="List of categories")
    total: int = Field(description="Total number of categories matching filter")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": "portrait",
                        "type": "subject",
                        "display_name": "Portrait",
                        "description": "Human portraits and headshots",
                        "keywords": {
                            "primary": ["portrait", "face", "person"],
                            "secondary": ["headshot", "closeup"],
                        },
                    }
                ],
                "total": 5,
                "page": 1,
                "page_size": 20,
            }
        }
    }


class CategorySearchResponse(BaseModel):
    """Category search response."""

    query: str = Field(description="The search query")
    results: list[Category] = Field(description="Matching categories")
    count: int = Field(description="Number of results")


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    type: CategoryType | None = Query(None, description="Filter by category type"),  # noqa: B008
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),  # noqa: B008
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),  # noqa: B008
) -> CategoryListResponse:
    """
    List all available categories.

    Optionally filter by type (subject, setting, modifier, style).
    Results are paginated.
    """
    registry = CategoryRegistry.get_instance()

    if type:
        all_categories = registry.get_by_type(type)
    else:
        all_categories = list(registry.all())

    total = len(all_categories)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_categories[start:end]

    return CategoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/search", response_model=CategorySearchResponse)
async def search_categories(
    q: str = Query(..., min_length=2, description="Search keyword or phrase"),  # noqa: B008
) -> CategorySearchResponse:
    """
    Search categories by keyword.

    Searches across primary, secondary, and specific keywords.
    Multi-word queries search each word and rank by match count.
    """
    registry = CategoryRegistry.get_instance()
    results = registry.search(q)

    return CategorySearchResponse(
        query=q,
        results=results,
        count=len(results),
    )


@router.get("/types", response_model=list[str])
async def list_category_types() -> list[str]:
    """
    List all category types.

    Returns the enum values for CategoryType.
    """
    return [t.value for t in CategoryType]


@router.get("/{category_id}", response_model=Category)
async def get_category(category_id: str) -> Category:
    """
    Get a single category by ID.

    Returns full category details including prompts, LoRAs, settings, and composition rules.
    """
    registry = CategoryRegistry.get_instance()
    category = registry.get(category_id)

    if category is None:
        raise HTTPException(status_code=404, detail=f"Category not found: {category_id}")

    return category
