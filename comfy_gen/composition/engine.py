"""Composition engine - merge categories into generation recipes.

The CompositionEngine handles:
- Resolving category IDs to Category objects
- Validating composition rules (conflicts, requirements)
- Merging prompt fragments
- Stacking LoRAs with conflict resolution
- Merging generation settings
- Selecting appropriate workflow
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .recipe import CompositionStep, LoraStack, Recipe

if TYPE_CHECKING:
    from comfy_gen.api.schemas.category import Category, LoraConfig
    from comfy_gen.categories.registry import CategoryRegistry

logger = logging.getLogger(__name__)


class CompositionError(Exception):
    """Raised when composition fails due to invalid category combination."""

    pass


class CompositionEngine:
    """Engine for composing multiple categories into a Recipe.

    The composition process:
    1. Resolve category IDs to Category objects
    2. Validate composition rules (max_concurrent, conflicts_with, requires)
    3. Merge prompt fragments (required first, then optional)
    4. Stack LoRAs with conflict detection
    5. Merge settings (with override order)
    6. Select workflow based on category types
    """

    def __init__(self, registry: CategoryRegistry | None = None) -> None:
        """Initialize the composition engine.

        Args:
            registry: Category registry to use. If None, uses singleton.
        """
        # Import here to avoid circular imports
        from comfy_gen.categories.registry import CategoryRegistry

        self.registry = registry or CategoryRegistry.get_instance()

    def compose(self, category_ids: list[str]) -> Recipe:
        """Compose categories into a generation recipe.

        Args:
            category_ids: List of category IDs to compose

        Returns:
            Recipe with merged parameters and provenance

        Raises:
            CompositionError: If composition fails (unknown category, conflict, etc.)
        """
        if not category_ids:
            raise CompositionError("No categories provided")

        # 1. Resolve categories
        categories = self._resolve_categories(category_ids)

        # 2. Validate composition rules
        self._validate_composition(categories)

        # 3. Build recipe
        steps: list[CompositionStep] = []
        warnings: list[str] = []

        # Log each category being added
        for cat in categories:
            steps.append(
                CompositionStep(
                    action="add_category",
                    source=cat.id,
                    detail=f"Adding {cat.type.value}: {cat.display_name}",
                )
            )

        # Merge prompts
        positive_parts, negative_parts = self._merge_prompts(categories, steps)

        # Stack LoRAs with conflict detection
        loras = self._stack_loras(categories, steps, warnings)

        # Merge settings
        settings = self._merge_settings(categories, steps)

        # Select workflow
        workflow = self._select_workflow(categories, steps)

        # Generate recipe ID
        recipe_id = Recipe.generate_id(category_ids)

        return Recipe(
            id=recipe_id,
            source_categories=category_ids,
            positive_prompt=", ".join(positive_parts),
            negative_prompt=", ".join(negative_parts),
            loras=loras,
            workflow=workflow,
            composition_steps=steps,
            warnings=warnings,
            **settings,
        )

    def _resolve_categories(self, category_ids: list[str]) -> list[Category]:
        """Resolve category IDs to Category objects.

        Args:
            category_ids: List of category IDs

        Returns:
            List of Category objects

        Raises:
            CompositionError: If any category ID is unknown
        """
        categories = []
        for cid in category_ids:
            cat = self.registry.get(cid)
            if cat is None:
                raise CompositionError(f"Unknown category: {cid}")
            categories.append(cat)
        return categories

    def _validate_composition(self, categories: list[Category]) -> None:
        """Validate composition rules.

        Checks:
        - conflicts_with: No conflicting categories
        - requires: All required categories present (if specified)
        - max_per_type: Not too many of the same type

        Args:
            categories: List of categories to validate

        Raises:
            CompositionError: If composition rules are violated
        """
        all_ids = {c.id for c in categories}

        # Count by type
        type_counts: dict[str, int] = {}
        for cat in categories:
            type_counts[cat.type.value] = type_counts.get(cat.type.value, 0) + 1

        for cat in categories:
            # Check conflicts
            conflicts = set(cat.composition.conflicts_with) & all_ids
            if conflicts:
                raise CompositionError(f"Category '{cat.id}' conflicts with: {conflicts}")

            # Check requires
            requires = set(cat.composition.requires) - all_ids
            if requires:
                raise CompositionError(f"Category '{cat.id}' requires categories not present: {requires}")

            # Check max_per_type
            if cat.composition.max_per_type is not None:
                if type_counts.get(cat.type.value, 0) > cat.composition.max_per_type:
                    raise CompositionError(
                        f"Too many {cat.type.value} categories "
                        f"(max {cat.composition.max_per_type} allowed by '{cat.id}')"
                    )

    def _merge_prompts(self, categories: list[Category], steps: list[CompositionStep]) -> tuple[list[str], list[str]]:
        """Merge prompt fragments from all categories.

        Order: required first, then optional.
        Deduplication preserves first occurrence.

        Args:
            categories: Categories to merge
            steps: Composition steps to append to

        Returns:
            Tuple of (positive_parts, negative_parts)
        """
        positive_parts: list[str] = []
        negative_parts: list[str] = []
        seen_positive: set[str] = set()
        seen_negative: set[str] = set()

        # Required prompts first
        for cat in categories:
            for fragment in cat.prompts.positive_fragments.required:
                if fragment.lower() not in seen_positive:
                    positive_parts.append(fragment)
                    seen_positive.add(fragment.lower())
            for fragment in cat.prompts.negative_fragments.required:
                if fragment.lower() not in seen_negative:
                    negative_parts.append(fragment)
                    seen_negative.add(fragment.lower())

        # Optional prompts second
        for cat in categories:
            for fragment in cat.prompts.positive_fragments.optional:
                if fragment.lower() not in seen_positive:
                    positive_parts.append(fragment)
                    seen_positive.add(fragment.lower())
            for fragment in cat.prompts.negative_fragments.optional:
                if fragment.lower() not in seen_negative:
                    negative_parts.append(fragment)
                    seen_negative.add(fragment.lower())

        steps.append(
            CompositionStep(
                action="merge_prompts",
                source="system",
                detail=f"Merged {len(positive_parts)} positive, {len(negative_parts)} negative fragments",
            )
        )

        return positive_parts, negative_parts

    def _stack_loras(
        self,
        categories: list[Category],
        steps: list[CompositionStep],
        warnings: list[str],
    ) -> list[LoraStack]:
        """Stack LoRAs from all categories with conflict detection.

        When the same LoRA appears in multiple categories:
        - Average the strengths
        - Merge trigger words
        - Record all source categories

        Args:
            categories: Categories to process
            steps: Composition steps to append to
            warnings: Warnings list to append to

        Returns:
            List of stacked LoRA configurations
        """
        lora_map: dict[str, LoraStack] = {}

        for cat in categories:
            # Process required LoRAs
            for lora in cat.loras.required:
                self._add_lora_to_stack(lora, cat.id, lora_map, steps, warnings)

            # Process recommended LoRAs
            for lora in cat.loras.recommended:
                self._add_lora_to_stack(lora, cat.id, lora_map, steps, warnings)

        return list(lora_map.values())

    def _add_lora_to_stack(
        self,
        lora: LoraConfig,
        cat_id: str,
        lora_map: dict[str, LoraStack],
        steps: list[CompositionStep],
        warnings: list[str],
    ) -> None:
        """Add a single LoRA to the stack.

        Args:
            lora: LoRA configuration from category
            cat_id: Source category ID
            lora_map: Map of filename -> LoraStack
            steps: Composition steps list
            warnings: Warnings list
        """
        if lora.filename in lora_map:
            # Conflict - same LoRA from multiple categories
            existing = lora_map[lora.filename]
            existing.source_categories.append(cat_id)

            # Average strengths
            n = len(existing.source_categories)
            existing.strength = (existing.strength * (n - 1) + lora.strength) / n

            # Merge trigger words
            for tw in lora.trigger_words:
                if tw not in existing.trigger_words:
                    existing.trigger_words.append(tw)

            warnings.append(f"LoRA '{lora.filename}' requested by multiple categories, averaged strength")
            steps.append(
                CompositionStep(
                    action="resolve_conflict",
                    source=cat_id,
                    detail=f"Averaged {lora.filename} strength to {existing.strength:.2f}",
                )
            )
        else:
            # New LoRA
            lora_map[lora.filename] = LoraStack(
                filename=lora.filename,
                strength=lora.strength,
                source_categories=[cat_id],
                trigger_words=list(lora.trigger_words),
            )
            steps.append(
                CompositionStep(
                    action="stack_lora",
                    source=cat_id,
                    detail=f"Added {lora.filename} at {lora.strength:.2f}",
                )
            )

    def _merge_settings(self, categories: list[Category], steps: list[CompositionStep]) -> dict:
        """Merge generation settings from categories.

        Strategy: Last category wins for explicit values.
        For ranges, use the midpoint.

        Args:
            categories: Categories to merge settings from
            steps: Composition steps to append to

        Returns:
            Dict of merged settings
        """
        # Defaults
        settings: dict = {
            "steps": 30,
            "cfg": 7.5,
            "width": 1024,
            "height": 1024,
            "sampler": None,
            "scheduler": None,
            "denoise": None,
            "checkpoint": None,
            "vae": None,
        }

        # Apply from each category (last wins for explicit values)
        for cat in categories:
            cat_settings = cat.settings

            # Steps range
            if cat_settings.steps is not None:
                if cat_settings.steps.default is not None:
                    settings["steps"] = int(cat_settings.steps.default)
                elif cat_settings.steps.min is not None and cat_settings.steps.max is not None:
                    settings["steps"] = (int(cat_settings.steps.min) + int(cat_settings.steps.max)) // 2

            # CFG range
            if cat_settings.cfg is not None:
                if cat_settings.cfg.default is not None:
                    settings["cfg"] = float(cat_settings.cfg.default)
                elif cat_settings.cfg.min is not None and cat_settings.cfg.max is not None:
                    settings["cfg"] = (float(cat_settings.cfg.min) + float(cat_settings.cfg.max)) / 2

            # Size
            if cat_settings.size is not None:
                if cat_settings.size.width is not None:
                    settings["width"] = cat_settings.size.width
                if cat_settings.size.height is not None:
                    settings["height"] = cat_settings.size.height

            # Direct settings
            if cat_settings.sampler is not None:
                settings["sampler"] = cat_settings.sampler
            if cat_settings.scheduler is not None:
                settings["scheduler"] = cat_settings.scheduler
            if cat_settings.denoise is not None:
                settings["denoise"] = cat_settings.denoise

        steps.append(
            CompositionStep(
                action="apply_settings",
                source="system",
                detail=f"Applied settings: steps={settings['steps']}, cfg={settings['cfg']:.1f}",
            )
        )

        return settings

    def _select_workflow(self, categories: list[Category], steps: list[CompositionStep]) -> str:
        """Select workflow from categories.

        Priority:
        1. Subject category workflow (if specified)
        2. Any category with workflow preference
        3. Default flux-dev.json

        Args:
            categories: Categories to select from
            steps: Composition steps to append to

        Returns:
            Workflow filename
        """
        # Import here for CategoryType
        from comfy_gen.api.schemas.category import CategoryType

        # Prefer subject category workflow
        for cat in categories:
            if cat.type == CategoryType.SUBJECT and cat.workflows:
                if cat.workflows.preferred:
                    workflow = cat.workflows.preferred[0]
                    steps.append(
                        CompositionStep(
                            action="select_workflow",
                            source=cat.id,
                            detail=f"Selected workflow '{workflow}' from subject category",
                        )
                    )
                    return workflow

        # Fallback to any workflow
        for cat in categories:
            if cat.workflows and cat.workflows.preferred:
                workflow = cat.workflows.preferred[0]
                steps.append(
                    CompositionStep(
                        action="select_workflow",
                        source=cat.id,
                        detail=f"Selected workflow '{workflow}'",
                    )
                )
                return workflow

        # Default
        workflow = "flux-dev.json"
        steps.append(
            CompositionStep(
                action="select_workflow",
                source="system",
                detail=f"Using default workflow '{workflow}'",
            )
        )
        return workflow
