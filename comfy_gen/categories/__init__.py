"""Category module - YAML schema, validation, and registry.

This package provides:
- JSON Schema validation for category YAML files (validator.py)
- CategoryRegistry for loading and querying categories (registry.py)
- Module-level convenience functions for common operations

Usage:
    from comfy_gen.categories import get_category, search_categories, CategoryRegistry

    # Get a specific category
    portrait = get_category("portrait")

    # Search by keyword
    results = search_categories("photo")

    # Get registry instance
    registry = CategoryRegistry.get_instance()
    for cat in registry.all():
        print(cat.id)
"""

from .registry import (
    CategoryRegistry,
    CategoryValidationError,
    get_categories_by_type,
    get_category,
    get_registry,
    search_categories,
)
from .validator import (
    check_schema_compatibility,
    get_schema,
    get_schema_version,
    validate_all_categories,
    validate_category,
    validate_category_file,
)

__all__ = [
    # Registry
    "CategoryRegistry",
    "CategoryValidationError",
    "get_registry",
    "get_category",
    "get_categories_by_type",
    "search_categories",
    # Validator
    "get_schema",
    "get_schema_version",
    "validate_category",
    "validate_category_file",
    "validate_all_categories",
    "check_schema_compatibility",
]
