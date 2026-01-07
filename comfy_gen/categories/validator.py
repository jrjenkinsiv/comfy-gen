"""Category schema validation utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union

import jsonschema
import yaml

logger = logging.getLogger(__name__)

# Load schema once at module import
_SCHEMA_PATH = Path(__file__).parent / "schema.json"
_SCHEMA: Optional[dict] = None


def get_schema() -> dict:
    """Load and cache the category JSON schema."""
    global _SCHEMA
    if _SCHEMA is None:
        with open(_SCHEMA_PATH) as f:
            _SCHEMA = json.load(f)
    return _SCHEMA


def validate_category(data: dict, filepath: Optional[Union[str, Path]] = None) -> list[str]:
    """
    Validate a category dict against the JSON schema.

    Args:
        data: Category data (parsed from YAML)
        filepath: Optional filepath for error context

    Returns:
        List of validation error messages (empty if valid)
    """
    schema = get_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = []

    for error in validator.iter_errors(data):
        path = ".".join(str(p) for p in error.absolute_path) or "root"
        context = f" in {filepath}" if filepath else ""
        errors.append(f"{path}: {error.message}{context}")

    return errors


def validate_category_file(filepath: Union[str, Path]) -> list[str]:
    """
    Load and validate a category YAML file.

    Args:
        filepath: Path to category YAML file

    Returns:
        List of validation error messages (empty if valid)
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return [f"File not found: {filepath}"]

    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if data is None:
        return [f"Empty file: {filepath}"]

    return validate_category(data, filepath)


def validate_all_categories(categories_dir: Optional[Union[str, Path]] = None) -> dict[str, list[str]]:
    """
    Validate all category YAML files in a directory.

    Args:
        categories_dir: Directory containing category files
                       (defaults to comfy_gen/categories/definitions/)

    Returns:
        Dict mapping filepath to list of errors (only files with errors)
    """
    if categories_dir is None:
        categories_dir = Path(__file__).parent / "definitions"

    categories_dir = Path(categories_dir)
    results = {}

    if not categories_dir.exists():
        logger.warning(f"Categories directory not found: {categories_dir}")
        return results

    for yaml_file in categories_dir.glob("**/*.yaml"):
        if yaml_file.name.startswith("_"):
            continue  # Skip files starting with underscore
        if yaml_file.name == "schema_version.yaml":
            continue  # Skip schema version file

        errors = validate_category_file(yaml_file)
        if errors:
            results[str(yaml_file)] = errors

    return results


def get_schema_version() -> str:
    """Get the current schema version."""
    version_file = Path(__file__).parent / "schema_version.yaml"
    with open(version_file) as f:
        data = yaml.safe_load(f)
    return data["schema"]["version"]


def check_schema_compatibility(category_version: str) -> bool:
    """
    Check if a category's schema version is compatible.

    Args:
        category_version: Version string from category file

    Returns:
        True if compatible, False otherwise
    """
    version_file = Path(__file__).parent / "schema_version.yaml"
    with open(version_file) as f:
        data = yaml.safe_load(f)

    min_supported = data["schema"]["minimum_supported"]

    # Simple semver comparison (major.minor.patch)
    def parse_version(v: str) -> tuple[int, int, int]:
        parts = v.split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    return parse_version(category_version) >= parse_version(min_supported)
