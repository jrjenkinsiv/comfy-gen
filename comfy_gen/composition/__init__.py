"""Composition module - merge categories into generation recipes.

This package provides:
- CompositionEngine for combining multiple categories
- Recipe model for composed generation parameters
- Conflict resolution for overlapping LoRAs and settings

Usage:
    from comfy_gen.composition import CompositionEngine, Recipe

    engine = CompositionEngine()
    recipe = engine.compose(["portrait", "night"])
    print(recipe.positive_prompt)
    print(recipe.loras)
"""

from .engine import CompositionEngine, CompositionError
from .recipe import CompositionStep, LoraStack, Recipe

__all__ = [
    "CompositionEngine",
    "CompositionError",
    "Recipe",
    "CompositionStep",
    "LoraStack",
]
