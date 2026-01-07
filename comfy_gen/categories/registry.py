"""Category registry with YAML loading, validation, and lookup.

This module provides the CategoryRegistry class which loads category YAML files,
validates them against the JSON Schema, and provides lookup interfaces.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

import jsonschema
import yaml

if TYPE_CHECKING:
    from comfy_gen.api.schemas.category import Category, CategoryType

logger = logging.getLogger(__name__)


class CategoryValidationError(Exception):
    """Raised when category YAML fails validation."""

    def __init__(self, filename: str, errors: list[str]) -> None:
        self.filename = filename
        self.errors = errors
        super().__init__(f"Invalid category {filename}: {errors}")


class CategoryRegistry:
    """Registry for category definitions with validation and lookup.

    This registry:
    - Loads all YAML files from the definitions/ directory
    - Validates each against the JSON Schema
    - Parses into Pydantic Category models
    - Provides lookup by ID, type, and keyword

    Uses singleton pattern via get_instance() for shared access.
    """

    _instance: CategoryRegistry | None = None

    def __init__(self, categories_dir: str | Path | None = None) -> None:
        """Initialize the registry.

        Args:
            categories_dir: Directory containing category YAML files.
                           Defaults to comfy_gen/categories/definitions/
        """
        # Import here to avoid circular imports
        from comfy_gen.api.schemas.category import CategoryType

        self._categories: dict[str, Category] = {}
        self._by_type: dict[CategoryType, list[Category]] = {t: [] for t in CategoryType}
        self._keyword_index: dict[str, list[str]] = {}  # keyword -> list of category IDs

        if categories_dir is None:
            categories_dir = Path(__file__).parent / "definitions"
        else:
            categories_dir = Path(categories_dir)

        self._categories_dir = categories_dir
        self._schema = self._load_schema()
        self._load_all_categories()

    @classmethod
    def get_instance(cls) -> CategoryRegistry:
        """Get singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reload(cls) -> CategoryRegistry:
        """Force reload of all categories."""
        cls._instance = None
        return cls.get_instance()

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def _load_schema(self) -> dict:
        """Load JSON Schema for validation."""
        schema_path = Path(__file__).parent / "schema.json"
        with open(schema_path) as f:
            return json.load(f)

    def _load_all_categories(self) -> None:
        """Load and validate all category YAML files recursively."""
        if not self._categories_dir.exists():
            logger.warning(f"Categories directory not found: {self._categories_dir}")
            return

        loaded_count = 0
        error_count = 0

        # Recursively find all YAML files in subdirectories
        for yaml_file in self._categories_dir.glob("**/*.yaml"):
            # Skip internal files
            if yaml_file.name.startswith("_"):
                continue
            if yaml_file.name == "schema_version.yaml":
                continue

            try:
                self._load_category_file(yaml_file)
                loaded_count += 1
            except CategoryValidationError as e:
                logger.error(f"Skipping invalid category: {e}")
                error_count += 1
            except yaml.YAMLError as e:
                logger.error(f"YAML parse error in {yaml_file}: {e}")
                error_count += 1
            except Exception as e:
                logger.error(f"Error loading {yaml_file}: {e}")
                error_count += 1

        # Log summary
        if loaded_count > 0:
            type_counts = {t.value: len(cats) for t, cats in self._by_type.items() if cats}
            logger.info(
                f"Loaded {loaded_count} categories: {type_counts}" + (f" ({error_count} errors)" if error_count else "")
            )
        elif error_count > 0:
            logger.warning(f"No categories loaded ({error_count} errors)")

    def _load_category_file(self, filepath: Path) -> None:
        """Load and validate a single category file."""
        # Import here to avoid circular imports
        from comfy_gen.api.schemas.category import Category

        with open(filepath) as f:
            data = yaml.safe_load(f)

        if data is None:
            raise CategoryValidationError(filepath.name, ["Empty file"])

        # JSON Schema validation
        try:
            jsonschema.validate(data, self._schema)
        except jsonschema.ValidationError as e:
            path = ".".join(str(p) for p in e.absolute_path) or "root"
            raise CategoryValidationError(filepath.name, [f"{path}: {e.message}"]) from e

        # Pydantic validation
        category = Category.model_validate(data["category"])

        # Check for duplicate IDs
        if category.id in self._categories:
            logger.warning(f"Duplicate category ID '{category.id}' in {filepath}, overwriting previous definition")

        # Register
        self._categories[category.id] = category
        self._by_type[category.type].append(category)

        # Index keywords for search
        for kw in category.keywords.primary:
            self._keyword_index.setdefault(kw.lower(), []).append(category.id)
        for kw in category.keywords.secondary:
            self._keyword_index.setdefault(kw.lower(), []).append(category.id)
        for kw in category.keywords.specific:
            self._keyword_index.setdefault(kw.lower(), []).append(category.id)

        logger.debug(f"Loaded category: {category.id} ({category.type.value})")

    def get(self, category_id: str) -> Category | None:
        """Get category by ID.

        Args:
            category_id: The unique category identifier

        Returns:
            Category if found, None otherwise
        """
        return self._categories.get(category_id)

    def get_by_type(self, category_type: CategoryType) -> list[Category]:
        """Get all categories of a given type.

        Args:
            category_type: The category type to filter by

        Returns:
            List of categories (may be empty)
        """
        return self._by_type.get(category_type, [])

    def search_by_keyword(self, keyword: str) -> list[Category]:
        """Find categories matching a keyword.

        Searches primary, secondary, and specific keywords.
        Case-insensitive.

        Args:
            keyword: The keyword to search for

        Returns:
            List of matching categories (may be empty)
        """
        category_ids = self._keyword_index.get(keyword.lower(), [])
        return [self._categories[cid] for cid in category_ids if cid in self._categories]

    def search(self, query: str) -> list[Category]:
        """Search categories by a query string.

        Splits query into words and finds categories matching any word.
        Returns unique categories sorted by match count (best first).

        Args:
            query: Search query string

        Returns:
            List of matching categories sorted by relevance
        """
        words = query.lower().split()
        if not words:
            return []

        # Count matches per category
        match_counts: dict[str, int] = {}
        for word in words:
            for cat_id in self._keyword_index.get(word, []):
                match_counts[cat_id] = match_counts.get(cat_id, 0) + 1

        # Sort by match count (descending)
        sorted_ids = sorted(match_counts.keys(), key=lambda x: match_counts[x], reverse=True)
        return [self._categories[cid] for cid in sorted_ids if cid in self._categories]

    def all(self) -> Iterator[Category]:
        """Iterate over all categories.

        Yields:
            Category objects in no particular order
        """
        yield from self._categories.values()

    def list_ids(self) -> list[str]:
        """Get list of all category IDs.

        Returns:
            List of category ID strings
        """
        return list(self._categories.keys())

    def __len__(self) -> int:
        """Return the number of loaded categories."""
        return len(self._categories)

    def __contains__(self, category_id: str) -> bool:
        """Check if a category ID exists."""
        return category_id in self._categories


# Module-level convenience functions for common operations


def get_registry() -> CategoryRegistry:
    """Get the singleton CategoryRegistry instance."""
    return CategoryRegistry.get_instance()


def get_category(category_id: str) -> Category | None:
    """Get a category by ID.

    Args:
        category_id: The unique category identifier

    Returns:
        Category if found, None otherwise
    """
    return CategoryRegistry.get_instance().get(category_id)


def get_categories_by_type(category_type: CategoryType) -> list[Category]:
    """Get all categories of a given type.

    Args:
        category_type: The category type to filter by

    Returns:
        List of categories
    """
    return CategoryRegistry.get_instance().get_by_type(category_type)


def search_categories(keyword: str) -> list[Category]:
    """Search categories by keyword.

    Args:
        keyword: The keyword to search for

    Returns:
        List of matching categories
    """
    return CategoryRegistry.get_instance().search_by_keyword(keyword)
