"""Generation pipeline - orchestrates the full generation process."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from ...api.schemas.generation import GenerationRequest
from ...api.schemas.recipe import Recipe
from .executor import ComfyUIExecutor

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from the generation pipeline."""

    image_url: str
    image_bytes: Optional[bytes]
    recipe: Recipe
    execution_time: float
    prompt_id: str


class GenerationPipeline:
    """
    Orchestrates the full generation process.

    Steps:
    1. Load workflow template
    2. Apply recipe settings to workflow
    3. Queue to ComfyUI
    4. Wait for completion
    5. Upload to MinIO
    6. Return result
    """

    def __init__(
        self,
        executor: Optional[ComfyUIExecutor] = None,
        workflows_dir: Union[str, Path] = "workflows",
    ):
        self.executor = executor or ComfyUIExecutor()
        self.workflows_dir = Path(workflows_dir)

    def load_workflow(self, workflow_name: str) -> dict:
        """Load a workflow JSON template."""
        workflow_path = self.workflows_dir / workflow_name

        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_path}")

        with open(workflow_path) as f:
            return json.load(f)

    def apply_recipe_to_workflow(
        self,
        workflow: dict,
        recipe: Recipe,
    ) -> dict:
        """
        Apply recipe settings to a workflow template.

        This modifies the workflow in place with:
        - Prompts
        - LoRAs
        - Generation settings (steps, cfg, size, etc.)
        """
        workflow = workflow.copy()

        # Find key nodes by class_type
        for _node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue

            class_type = node.get("class_type", "")
            inputs = node.get("inputs", {})

            # Apply prompts to CLIP text encode nodes
            if class_type in ("CLIPTextEncode", "CLIPTextEncodeSDXL"):
                # Determine if positive or negative by node title or position
                title = node.get("_meta", {}).get("title", "").lower()
                if "negative" in title or "neg" in title:
                    inputs["text"] = recipe.negative_prompt
                else:
                    inputs["text"] = recipe.positive_prompt

            # Apply sampler settings
            if class_type in ("KSampler", "KSamplerAdvanced"):
                if recipe.seed >= 0:
                    inputs["seed"] = recipe.seed
                inputs["steps"] = recipe.steps
                inputs["cfg"] = recipe.cfg
                inputs["sampler_name"] = recipe.sampler
                inputs["scheduler"] = recipe.scheduler
                if recipe.denoise < 1.0:
                    inputs["denoise"] = recipe.denoise

            # Apply image size to empty latent
            if class_type == "EmptyLatentImage":
                inputs["width"] = recipe.width
                inputs["height"] = recipe.height

        return workflow

    def build_recipe_from_request(self, request: GenerationRequest) -> Recipe:
        """
        Build a Recipe from a GenerationRequest.

        This is the simple case - direct parameters without composition.
        """
        from ...api.schemas.recipe import LoRAConfig

        loras = []
        if request.loras:
            for lora in request.loras:
                loras.append(
                    LoRAConfig(
                        filename=lora["filename"],
                        strength=lora.get("strength", 0.8),
                    )
                )

        return Recipe(
            source_categories=request.categories,
            workflow=request.workflow,
            positive_prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            loras=loras,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg=request.cfg,
            seed=request.seed,
        )

    async def execute(
        self,
        request: GenerationRequest,
        client_id: Optional[str] = None,
    ) -> PipelineResult:
        """
        Execute the full generation pipeline.

        Args:
            request: Generation request with all parameters
            client_id: Optional client ID for WebSocket updates

        Returns:
            PipelineResult with image URL and metadata
        """
        # Build recipe from request
        recipe = self.build_recipe_from_request(request)

        # Load and configure workflow
        workflow = self.load_workflow(recipe.workflow)
        workflow = self.apply_recipe_to_workflow(workflow, recipe)

        # Queue to ComfyUI
        prompt_id = await self.executor.queue_prompt(workflow, client_id)

        # Wait for completion
        result = await self.executor.wait_for_completion(prompt_id)

        # Get the first output image
        if not result.images:
            raise RuntimeError("No images generated")

        first_image = result.images[0]
        image_bytes = await self.executor.get_image(
            filename=first_image["filename"],
            subfolder=first_image.get("subfolder", ""),
            folder_type=first_image.get("type", "output"),
        )

        # TODO: Upload to MinIO and get URL
        # For now, construct a placeholder URL
        image_url = f"http://192.168.1.215:9000/comfy-gen/{first_image['filename']}"

        return PipelineResult(
            image_url=image_url,
            image_bytes=image_bytes,
            recipe=recipe,
            execution_time=result.execution_time,
            prompt_id=prompt_id,
        )
