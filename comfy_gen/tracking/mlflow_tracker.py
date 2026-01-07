"""MLflow integration for generation provenance tracking.

Tracks generation experiments with recipe hashes for reproducibility
and drift detection when category definitions change.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from comfy_gen.composition.recipe import Recipe

logger = logging.getLogger(__name__)

# MLflow imports - optional dependency
try:
    import mlflow
    from mlflow.tracking import MlflowClient

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None  # type: ignore
    MlflowClient = None  # type: ignore


@dataclass
class ProvenanceHashes:
    """Hash values for provenance tracking.

    Attributes:
        recipe_hash: Hash of recipe content (prompts, loras, settings)
        category_hash: Hash of category definitions used
        combined_hash: Combined hash for exact reproducibility
    """

    recipe_hash: str
    category_hash: str
    combined_hash: str


@dataclass
class GenerationResult:
    """Result of a generation for logging purposes."""

    generation_id: str
    output_url: Optional[str] = None
    generation_time: Optional[float] = None
    status: str = "completed"


class MLflowTracker:
    """MLflow integration for generation provenance tracking.

    Logs generation params, recipes, and results to MLflow with
    deterministic hashes for drift detection.
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        experiment_name: str = "comfy-gen-intelligent",
    ) -> None:
        """Initialize the MLflow tracker.

        Args:
            tracking_uri: MLflow tracking server URI.
                         Defaults to MLFLOW_TRACKING_URI env var or cerebro.
            experiment_name: Name of the MLflow experiment
        """
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not installed - tracking disabled")
            self._enabled = False
            return

        self._enabled = True
        self.tracking_uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "http://192.168.1.162:5001")
        self.experiment_name = experiment_name

        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(experiment_name)

        self.client = MlflowClient(self.tracking_uri)
        logger.info(f"MLflow tracker initialized: {self.tracking_uri}")

    @property
    def enabled(self) -> bool:
        """Whether MLflow tracking is enabled."""
        return self._enabled

    @property
    def experiment_id(self) -> Optional[str]:
        """Get the current experiment ID."""
        if not self._enabled:
            return None
        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        return experiment.experiment_id if experiment else None

    def compute_recipe_hash(self, recipe: Recipe) -> str:
        """Compute deterministic hash of recipe content.

        Hash includes: categories, prompts, loras, settings.
        Excludes: timestamps, generation IDs.

        Args:
            recipe: Recipe to hash

        Returns:
            16-character hex string
        """
        content = {
            "source_categories": sorted(recipe.source_categories),
            "positive_prompt": recipe.positive_prompt,
            "negative_prompt": recipe.negative_prompt,
            "loras": [
                {"filename": lora.filename, "strength": lora.strength}
                for lora in sorted(recipe.loras, key=lambda x: x.filename)
            ],
            "steps": recipe.steps,
            "cfg": recipe.cfg,
            "workflow": recipe.workflow,
        }
        json_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]

    def compute_category_hash(self, category_ids: list[str]) -> str:
        """Compute hash of category definitions.

        Used to detect when category YAML files have changed.

        Args:
            category_ids: List of category IDs to hash

        Returns:
            16-character hex string
        """
        from comfy_gen.categories.registry import CategoryRegistry

        registry = CategoryRegistry.get_instance()

        definitions = {}
        for cat_id in sorted(category_ids):
            cat = registry.get(cat_id)
            if cat:
                # Hash significant fields
                definitions[cat_id] = {
                    "schema_version": cat.schema_version,
                    "keywords": cat.keywords.model_dump(),
                    "prompts": cat.prompts.model_dump(),
                    "loras": cat.loras.model_dump(),
                }

        json_str = json.dumps(definitions, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]

    def compute_provenance(self, recipe: Recipe) -> ProvenanceHashes:
        """Compute all provenance hashes for a recipe.

        Args:
            recipe: Recipe to compute hashes for

        Returns:
            ProvenanceHashes with recipe, category, and combined hashes
        """
        recipe_hash = self.compute_recipe_hash(recipe)
        category_hash = self.compute_category_hash(recipe.source_categories)
        combined_hash = hashlib.sha256(f"{recipe_hash}:{category_hash}".encode()).hexdigest()[:16]

        return ProvenanceHashes(
            recipe_hash=recipe_hash,
            category_hash=category_hash,
            combined_hash=combined_hash,
        )

    def log_generation(
        self,
        recipe: Recipe,
        result: GenerationResult,
        user_rating: Optional[int] = None,
        feedback: Optional[str] = None,
    ) -> Optional[str]:
        """Log generation to MLflow with full provenance.

        Args:
            recipe: The composed recipe
            result: Generation result with output URL and timing
            user_rating: Optional user rating (1-5)
            feedback: Optional user feedback text

        Returns:
            MLflow run_id or None if tracking disabled
        """
        if not self._enabled:
            logger.debug("MLflow tracking disabled - skipping log")
            return None

        provenance = self.compute_provenance(recipe)

        with mlflow.start_run() as run:
            # Log parameters
            mlflow.log_params(
                {
                    "workflow": recipe.workflow,
                    "steps": recipe.steps,
                    "cfg": recipe.cfg,
                    "width": recipe.width,
                    "height": recipe.height,
                    "checkpoint": recipe.checkpoint or "default",
                    "lora_count": len(recipe.loras),
                    "category_count": len(recipe.source_categories),
                }
            )

            # Log prompts (truncated if too long)
            mlflow.log_params(
                {
                    "positive_prompt": recipe.positive_prompt[:250],
                    "negative_prompt": recipe.negative_prompt[:250],
                }
            )

            # Log individual LoRAs (max 5 for MLflow param limits)
            for i, lora in enumerate(recipe.loras[:5]):
                mlflow.log_param(f"lora_{i}_name", lora.filename)
                mlflow.log_param(f"lora_{i}_strength", lora.strength)

            # Log metrics
            if result.generation_time:
                mlflow.log_metric("generation_time_sec", result.generation_time)

            if user_rating is not None:
                mlflow.log_metric("user_rating", user_rating)

            # Log provenance tags
            mlflow.set_tags(
                {
                    "recipe_hash": provenance.recipe_hash,
                    "category_hash": provenance.category_hash,
                    "combined_hash": provenance.combined_hash,
                    "source_categories": ",".join(recipe.source_categories),
                    "image_url": result.output_url or "",
                    "generation_id": result.generation_id,
                }
            )

            if feedback:
                mlflow.set_tag("user_feedback", feedback[:500])

            # Log recipe as artifact
            mlflow.log_dict(recipe.model_dump(), "recipe.json")

            logger.info(f"Logged generation to MLflow: run_id={run.info.run_id}")
            return run.info.run_id

    def find_runs_by_recipe_hash(self, recipe_hash: str) -> list[dict]:
        """Find all runs with matching recipe hash.

        Args:
            recipe_hash: Recipe hash to search for

        Returns:
            List of run info dicts
        """
        if not self._enabled or not self.experiment_id:
            return []

        runs = self.client.search_runs(
            experiment_ids=[self.experiment_id],
            filter_string=f'tags.recipe_hash = "{recipe_hash}"',
        )

        return [
            {
                "run_id": r.info.run_id,
                "user_rating": r.data.metrics.get("user_rating"),
                "category_hash": r.data.tags.get("category_hash"),
                "timestamp": r.info.start_time,
                "image_url": r.data.tags.get("image_url"),
            }
            for r in runs
        ]

    def detect_category_drift(self, recipe: Recipe) -> dict:
        """Detect if category definitions have changed since last run.

        Args:
            recipe: Recipe to check for drift

        Returns:
            Dict with has_drift, reason, and hash info
        """
        if not self._enabled:
            return {
                "has_drift": False,
                "reason": "tracking_disabled",
            }

        recipe_hash = self.compute_recipe_hash(recipe)
        current_category_hash = self.compute_category_hash(recipe.source_categories)

        previous_runs = self.find_runs_by_recipe_hash(recipe_hash)

        if not previous_runs:
            return {
                "has_drift": False,
                "reason": "no_previous_runs",
                "current_hash": current_category_hash,
            }

        # Check most recent run
        latest = max(previous_runs, key=lambda r: r["timestamp"])
        previous_hash = latest["category_hash"]

        if previous_hash != current_category_hash:
            return {
                "has_drift": True,
                "reason": "category_definition_changed",
                "previous_hash": previous_hash,
                "current_hash": current_category_hash,
                "previous_run_id": latest["run_id"],
            }

        return {
            "has_drift": False,
            "reason": "no_changes",
            "current_hash": current_category_hash,
        }

    def get_best_rated_runs(
        self,
        min_rating: int = 4,
        limit: int = 10,
    ) -> list[dict]:
        """Get highest-rated runs.

        Args:
            min_rating: Minimum rating threshold
            limit: Maximum runs to return

        Returns:
            List of run info dicts
        """
        if not self._enabled or not self.experiment_id:
            return []

        runs = self.client.search_runs(
            experiment_ids=[self.experiment_id],
            filter_string=f"metrics.user_rating >= {min_rating}",
            order_by=["metrics.user_rating DESC"],
            max_results=limit,
        )

        return [
            {
                "run_id": r.info.run_id,
                "user_rating": r.data.metrics.get("user_rating"),
                "recipe_hash": r.data.tags.get("recipe_hash"),
                "categories": r.data.tags.get("source_categories", "").split(","),
                "image_url": r.data.tags.get("image_url"),
            }
            for r in runs
        ]


# Module-level singleton instance
_tracker: Optional[MLflowTracker] = None


def get_tracker() -> MLflowTracker:
    """Get or create the global MLflow tracker instance.

    Returns:
        MLflowTracker singleton
    """
    global _tracker
    if _tracker is None:
        _tracker = MLflowTracker()
    return _tracker
