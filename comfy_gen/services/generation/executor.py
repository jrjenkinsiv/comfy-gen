"""ComfyUI API executor - handles all ComfyUI server interactions."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ExecutionProgress:
    """Progress information from ComfyUI."""

    prompt_id: str
    current_node: str | None = None
    current_step: int = 0
    total_steps: int = 0
    preview_image: bytes | None = None


@dataclass
class ExecutionResult:
    """Result from a ComfyUI execution."""

    prompt_id: str
    images: list[dict]  # [{"filename": "...", "subfolder": "...", "type": "output"}]
    execution_time: float


class ComfyUIExecutor:
    """
    Handles all ComfyUI API interactions.

    Methods:
    - queue_prompt(): Submit workflow to ComfyUI queue
    - get_history(): Retrieve execution history
    - get_image(): Download generated image
    - connect_websocket(): Real-time progress updates
    """

    def __init__(self, server_address: str = "192.168.1.215:8188"):
        self.server_address = server_address
        self.base_url = f"http://{server_address}"

    async def queue_prompt(
        self,
        workflow: dict,
        client_id: str | None = None,
    ) -> str:
        """
        Queue a prompt/workflow for execution.

        Args:
            workflow: ComfyUI workflow JSON
            client_id: Optional client ID for WebSocket updates

        Returns:
            prompt_id for tracking
        """
        async with aiohttp.ClientSession() as session:
            payload: dict[str, Any] = {"prompt": workflow}
            if client_id:
                payload["client_id"] = client_id

            async with session.post(
                f"{self.base_url}/prompt",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Failed to queue prompt: {resp.status} - {text}")

                result = await resp.json()
                prompt_id = result.get("prompt_id")

                if not prompt_id:
                    raise RuntimeError(f"No prompt_id in response: {result}")

                logger.info(f"Queued prompt: {prompt_id}")
                return prompt_id

    async def get_history(self, prompt_id: str) -> dict | None:
        """
        Get execution history for a prompt.

        Returns None if prompt hasn't completed yet.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/history/{prompt_id}") as resp:
                if resp.status == 200:
                    history = await resp.json()
                    return history.get(prompt_id)
                return None

    async def get_image(
        self,
        filename: str,
        subfolder: str = "",
        folder_type: str = "output",
    ) -> bytes:
        """
        Retrieve a generated image.

        Args:
            filename: Image filename
            subfolder: Subfolder within output directory
            folder_type: Usually "output" for generated images

        Returns:
            Image bytes
        """
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/view", params=params) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to get image: {resp.status}")
                return await resp.read()

    async def get_system_stats(self) -> dict:
        """Get ComfyUI system statistics (GPU, memory, etc.)."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/system_stats") as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}

    async def get_queue(self) -> dict:
        """Get current queue status."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/queue") as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"queue_running": [], "queue_pending": []}

    async def interrupt(self) -> bool:
        """Interrupt current execution."""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/interrupt") as resp:
                return resp.status == 200

    async def wait_for_completion(
        self,
        prompt_id: str,
        timeout: float = 300.0,
        poll_interval: float = 0.5,
    ) -> ExecutionResult:
        """
        Poll until execution completes.

        Args:
            prompt_id: Prompt ID to wait for
            timeout: Maximum wait time in seconds
            poll_interval: Time between polls

        Returns:
            ExecutionResult with output images

        Raises:
            TimeoutError if timeout exceeded
            RuntimeError if execution failed
        """
        import time

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Execution timeout after {timeout}s")

            history = await self.get_history(prompt_id)

            if history is not None:
                # Check for errors
                if "status" in history and history["status"].get("status_str") == "error":
                    error_msg = history["status"].get("error", "Unknown error")
                    raise RuntimeError(f"Execution failed: {error_msg}")

                # Get output images
                outputs = history.get("outputs", {})
                images = []

                for _node_id, node_output in outputs.items():
                    if "images" in node_output:
                        images.extend(node_output["images"])

                if images:
                    return ExecutionResult(
                        prompt_id=prompt_id,
                        images=images,
                        execution_time=elapsed,
                    )

            await asyncio.sleep(poll_interval)

    async def check_health(self) -> bool:
        """Check if ComfyUI server is responsive."""
        try:
            stats = await self.get_system_stats()
            return bool(stats)
        except Exception:
            return False
