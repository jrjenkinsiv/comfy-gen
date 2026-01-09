"""Generation service that wraps generate.py logic."""

import os
import random
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import generate
from clients.comfyui_client import ComfyUIClient
from clients.minio_client import MinIOClient

# Job status constants
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Configuration from environment or defaults
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.1.215:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "comfy-gen")


class GenerationJob:
    """Represents a generation job."""

    def __init__(
        self,
        job_id: str,
        prompt: str,
        negative_prompt: str,
        workflow: str,
        width: int,
        height: int,
        steps: int,
        cfg: float,
        seed: int,
        loras: list[str],
        sampler: Optional[str] = None,
        scheduler: Optional[str] = None,
    ):
        """Initialize generation job."""
        self.job_id = job_id
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.workflow = workflow
        self.width = width
        self.height = height
        self.steps = steps
        self.cfg = cfg
        self.seed = seed
        self.loras = loras
        self.sampler = sampler
        self.scheduler = scheduler

        self.status = STATUS_QUEUED
        self.progress = 0.0
        self.image_url: Optional[str] = None
        self.error: Optional[str] = None
        self.prompt_id: Optional[str] = None

        # Progress tracking
        self.current_step: Optional[int] = None
        self.max_steps: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "image_url": self.image_url,
            "error": self.error,
        }


class GenerationService:
    """Service for managing image generation jobs."""

    def __init__(self):
        """Initialize generation service."""
        self.jobs: Dict[str, GenerationJob] = {}
        self.lock = threading.Lock()
        self.comfyui_client = ComfyUIClient()
        self.minio_client = MinIOClient()

    def create_job(
        self,
        prompt: str,
        negative_prompt: str = "",
        workflow: str = "flux-dev.json",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg: float = 7.0,
        seed: int = -1,
        loras: Optional[list[str]] = None,
        sampler: Optional[str] = None,
        scheduler: Optional[str] = None,
    ) -> str:
        """Create a new generation job.

        Args:
            prompt: Positive text prompt
            negative_prompt: Negative text prompt
            workflow: Workflow filename
            width: Output width
            height: Output height
            steps: Sampling steps
            cfg: CFG scale
            seed: Random seed (-1 for random)
            loras: LoRA specifications
            sampler: Sampler algorithm
            scheduler: Scheduler

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        if loras is None:
            loras = []

        job = GenerationJob(
            job_id=job_id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            workflow=workflow,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            seed=seed,
            loras=loras,
            sampler=sampler,
            scheduler=scheduler,
        )

        with self.lock:
            self.jobs[job_id] = job

        # Start generation in background thread
        thread = threading.Thread(target=self._execute_job, args=(job,), daemon=True)
        thread.start()

        return job_id

    def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            GenerationJob or None if not found
        """
        with self.lock:
            return self.jobs.get(job_id)

    def _execute_job(self, job: GenerationJob):
        """Execute a generation job (runs in background thread).

        Args:
            job: GenerationJob to execute
        """
        try:
            # Update status to running
            with self.lock:
                job.status = STATUS_RUNNING

            # Resolve workflow path
            workflow_path = Path("workflows") / job.workflow
            if not workflow_path.exists():
                raise FileNotFoundError(f"Workflow not found: {workflow_path}")

            # Load workflow
            workflow = generate.load_workflow(str(workflow_path))

            # Apply modifications
            workflow = generate.modify_prompt(workflow, job.prompt, job.negative_prompt)
            workflow = generate.modify_dimensions(workflow, job.width, job.height)

            # Handle seed
            actual_seed = job.seed if job.seed >= 0 else random.randint(0, 2**32 - 1)
            workflow = generate.modify_sampler_params(
                workflow,
                steps=job.steps,
                cfg=job.cfg,
                seed=actual_seed,
                sampler_name=job.sampler,
                scheduler=job.scheduler,
            )

            # Inject LoRAs if specified
            if job.loras:
                workflow = generate.inject_lora_chain(workflow, job.loras)

            # Queue workflow
            prompt_id = self.comfyui_client.queue_prompt(workflow)
            if not prompt_id:
                raise RuntimeError("Failed to queue workflow with ComfyUI")

            with self.lock:
                job.prompt_id = prompt_id

            # Wait for completion with progress tracking
            def progress_callback(progress_data: Dict[str, Any]):
                """Update job progress."""
                with self.lock:
                    if "step" in progress_data and "max_steps" in progress_data:
                        job.current_step = progress_data["step"]
                        job.max_steps = progress_data["max_steps"]
                        if job.max_steps > 0:
                            job.progress = job.current_step / job.max_steps

            result = self.comfyui_client.wait_for_completion(
                prompt_id, timeout=600, poll_interval=2.0, progress_callback=progress_callback
            )

            if not result:
                raise RuntimeError("Generation timed out")

            # Check for errors
            if "status" in result:
                status_info = result["status"]
                if status_info.get("status_str") == "error":
                    error_messages = status_info.get("messages", [])
                    error_text = "; ".join([str(msg) for msg in error_messages]) if error_messages else "Unknown error"
                    raise RuntimeError(f"Generation failed: {error_text}")

            # Extract image from outputs
            image_url = None
            if "outputs" in result:
                for _node_id, node_output in result["outputs"].items():
                    if "images" in node_output:
                        images = node_output["images"]
                        if images:
                            # Get first image
                            image_info = images[0]
                            filename = image_info.get("filename")

                            if filename:
                                # Construct MinIO URL
                                # ComfyUI saves to output directory, which is synced to MinIO
                                image_url = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{filename}"
                                break

            if not image_url:
                raise RuntimeError("No image output found in generation result")

            # Update job with success
            with self.lock:
                job.status = STATUS_COMPLETED
                job.progress = 1.0
                job.image_url = image_url

        except Exception as e:
            # Update job with error
            with self.lock:
                job.status = STATUS_FAILED
                job.error = str(e)


# Global service instance
_service_instance: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    """Get the global generation service instance.

    Returns:
        GenerationService singleton
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = GenerationService()
    return _service_instance
