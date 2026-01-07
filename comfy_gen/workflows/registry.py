"""Workflow manifest registry.

Discovers and loads workflow manifests from workflow JSON files
and optional YAML override files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import yaml

from comfy_gen.workflows.manifest import (
    LoraConstraint,
    WorkflowManifest,
)

if TYPE_CHECKING:
    from comfy_gen.composition.recipe import Recipe

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """Registry for workflow manifests.

    Discovers workflows from a directory, auto-generates manifests from
    workflow JSON when possible, and loads manual manifest overrides.
    """

    _instance: Optional[WorkflowRegistry] = None

    def __init__(self, workflows_dir: Optional[Union[Path, str]] = None) -> None:
        """Initialize the workflow registry.

        Args:
            workflows_dir: Directory containing workflow JSON files.
                          Defaults to project's workflows/ directory.
        """
        if workflows_dir is None:
            # Default to project's workflows directory
            workflows_dir = Path(__file__).parent.parent.parent / "workflows"
        self._workflows_dir = Path(workflows_dir)
        self._manifests: dict[str, WorkflowManifest] = {}
        self._discover_manifests()

    @classmethod
    def get_instance(cls, workflows_dir: Optional[Union[Path, str]] = None) -> WorkflowRegistry:
        """Get or create singleton instance.

        Args:
            workflows_dir: Optional workflows directory

        Returns:
            WorkflowRegistry instance
        """
        if cls._instance is None:
            cls._instance = cls(workflows_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def _discover_manifests(self) -> None:
        """Discover and load all workflow manifests."""
        if not self._workflows_dir.exists():
            logger.warning(f"Workflows directory not found: {self._workflows_dir}")
            return

        for workflow_file in self._workflows_dir.glob("*.json"):
            # Skip non-workflow JSON files
            if workflow_file.name.startswith("."):
                continue

            try:
                manifest = self._load_or_generate_manifest(workflow_file)
                workflow_name = workflow_file.stem
                self._manifests[workflow_name] = manifest
                logger.debug(f"Loaded manifest for {workflow_name}")
            except Exception as e:
                logger.error(f"Failed to load manifest for {workflow_file}: {e}")

        logger.info(f"Discovered {len(self._manifests)} workflow manifests")

    def _load_or_generate_manifest(self, workflow_file: Path) -> WorkflowManifest:
        """Load manifest from YAML or auto-generate from workflow.

        Args:
            workflow_file: Path to workflow JSON file

        Returns:
            WorkflowManifest for the workflow
        """
        # Check for manual manifest override
        manifest_file = workflow_file.with_suffix(".manifest.yaml")

        if manifest_file.exists():
            logger.debug(f"Loading manifest from {manifest_file}")
            with manifest_file.open() as f:
                data = yaml.safe_load(f)
            return WorkflowManifest(**data)

        # Auto-generate from workflow analysis
        return self._generate_manifest(workflow_file)

    def _generate_manifest(self, workflow_file: Path) -> WorkflowManifest:
        """Auto-generate manifest by analyzing workflow JSON.

        Best-effort analysis - manual manifests preferred for accuracy.

        Args:
            workflow_file: Path to workflow JSON file

        Returns:
            Auto-generated WorkflowManifest
        """
        with workflow_file.open() as f:
            workflow = json.load(f)

        # Analyze workflow nodes
        nodes = workflow if isinstance(workflow, dict) else {}
        node_str = json.dumps(nodes)

        has_controlnet = "ControlNet" in node_str or "controlnet" in node_str.lower()
        has_video = any(x in node_str for x in ["Video", "AnimateDiff", "ImageSequence", "WanVideo"])
        has_img2img = "img2img" in node_str.lower() or "image2image" in node_str.lower()
        has_inpainting = "inpaint" in node_str.lower()
        has_upscale = "upscale" in node_str.lower() or "Upscale" in node_str

        # Count LoRA loaders
        lora_count = 0
        for node_data in nodes.values():
            if isinstance(node_data, dict):
                class_type = str(node_data.get("class_type", ""))
                if "LoraLoader" in class_type or "Lora" in class_type:
                    lora_count += 1

        # Detect checkpoint type from workflow name or nodes
        checkpoint_type = None
        workflow_lower = workflow_file.name.lower()
        if "flux" in workflow_lower:
            checkpoint_type = "flux"
        elif "sdxl" in workflow_lower or "xl" in workflow_lower:
            checkpoint_type = "sdxl"
        elif "sd15" in workflow_lower or "sd1.5" in workflow_lower:
            checkpoint_type = "sd15"
        elif "wan" in workflow_lower:
            checkpoint_type = "wan"

        return WorkflowManifest(
            workflow_file=workflow_file.name,
            display_name=workflow_file.stem.replace("-", " ").replace("_", " ").title(),
            description=f"Auto-generated manifest for {workflow_file.name}",
            supports_controlnet=has_controlnet,
            supports_video=has_video,
            supports_img2img=has_img2img,
            supports_inpainting=has_inpainting,
            supports_upscale=has_upscale,
            loras=LoraConstraint(max_loras=max(lora_count, 3)),
            checkpoints=({"required_type": checkpoint_type} if checkpoint_type else {}),  # type: ignore
        )

    def get(self, workflow_name: str) -> Optional[WorkflowManifest]:
        """Get manifest for a workflow by name.

        Args:
            workflow_name: Workflow name (without .json extension)

        Returns:
            WorkflowManifest or None if not found
        """
        # Try exact match
        if workflow_name in self._manifests:
            return self._manifests[workflow_name]

        # Try with .json stripped
        clean_name = workflow_name.replace(".json", "")
        return self._manifests.get(clean_name)

    def all(self) -> list[WorkflowManifest]:
        """Get all workflow manifests.

        Returns:
            List of all WorkflowManifest objects
        """
        return list(self._manifests.values())

    def get_by_capability(
        self,
        *,
        supports_video: Optional[bool] = None,
        supports_controlnet: Optional[bool] = None,
        supports_img2img: Optional[bool] = None,
        checkpoint_type: Optional[str] = None,
    ) -> list[WorkflowManifest]:
        """Find workflows matching capability requirements.

        Args:
            supports_video: Filter by video support
            supports_controlnet: Filter by ControlNet support
            supports_img2img: Filter by img2img support
            checkpoint_type: Filter by checkpoint type

        Returns:
            List of matching WorkflowManifest objects
        """
        results = []

        for manifest in self._manifests.values():
            # Check each filter
            if supports_video is not None and manifest.supports_video != supports_video:
                continue
            if supports_controlnet is not None and manifest.supports_controlnet != supports_controlnet:
                continue
            if supports_img2img is not None and manifest.supports_img2img != supports_img2img:
                continue
            if checkpoint_type is not None:
                if manifest.checkpoints.required_type != checkpoint_type:
                    continue

            results.append(manifest)

        return results

    def validate_recipe(
        self,
        recipe: Recipe,
        manifest: WorkflowManifest,
    ) -> list[str]:
        """Validate recipe against workflow constraints.

        Args:
            recipe: Recipe to validate
            manifest: Workflow manifest with constraints

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Check LoRA count
        if len(recipe.loras) > manifest.loras.max_loras:
            errors.append(f"Recipe has {len(recipe.loras)} LoRAs but workflow supports max {manifest.loras.max_loras}")

        # Check resolution
        if recipe.width < manifest.resolution.min_width:
            errors.append(f"Width {recipe.width} below minimum {manifest.resolution.min_width}")
        if recipe.width > manifest.resolution.max_width:
            errors.append(f"Width {recipe.width} exceeds maximum {manifest.resolution.max_width}")
        if recipe.height < manifest.resolution.min_height:
            errors.append(f"Height {recipe.height} below minimum {manifest.resolution.min_height}")
        if recipe.height > manifest.resolution.max_height:
            errors.append(f"Height {recipe.height} exceeds maximum {manifest.resolution.max_height}")

        # Check LoRA strengths
        for lora in recipe.loras:
            if lora.strength < manifest.loras.min_strength:
                errors.append(
                    f"LoRA {lora.filename} strength {lora.strength} below minimum {manifest.loras.min_strength}"
                )
            if lora.strength > manifest.loras.max_strength:
                errors.append(
                    f"LoRA {lora.filename} strength {lora.strength} exceeds maximum {manifest.loras.max_strength}"
                )

        return errors

    def __len__(self) -> int:
        """Return number of workflows in registry."""
        return len(self._manifests)

    def __contains__(self, name: str) -> bool:
        """Check if workflow exists in registry."""
        return name in self._manifests or name.replace(".json", "") in self._manifests
