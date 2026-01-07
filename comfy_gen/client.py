"""
Typed HTTP client for comfy-gen API.

Shared by CLI and MCP Server - provides type-safe access to all API endpoints.
Auto-validates requests/responses against Pydantic schemas.
"""
import asyncio
import logging
from typing import Any, AsyncIterator

import httpx

from .api.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
)
from .api.schemas.recipe import Recipe

logger = logging.getLogger(__name__)


class ComfyGenError(Exception):
    """Base exception for ComfyGen client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ComfyGenClient:
    """
    Typed HTTP client for comfy-gen API.

    Provides type-safe access to all API endpoints with:
    - Automatic request/response validation via Pydantic
    - Async support for generation polling
    - WebSocket connection for real-time progress (future)

    Usage:
        # Sync usage (CLI)
        client = ComfyGenClient("http://localhost:8000")
        response = client.generate(GenerationRequest(prompt="a cat"))
        result = client.wait_for_completion(response.generation_id)

        # Async usage (MCP server)
        async with ComfyGenClient("http://localhost:8000") as client:
            response = await client.generate_async(request)
            async for status in client.poll_status(response.generation_id):
                print(status.progress)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    # Context managers for async usage
    async def __aenter__(self) -> "ComfyGenClient":
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._async_client

    def close(self) -> None:
        """Close sync client connection."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    def _handle_error(self, response: httpx.Response) -> None:
        """Raise appropriate error for non-2xx responses."""
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise ComfyGenError(detail, status_code=response.status_code)

    # ============================================================
    # HEALTH ENDPOINTS
    # ============================================================

    def health(self) -> dict:
        """GET /health - Check API server health."""
        response = self._get_sync_client().get("/health")
        self._handle_error(response)
        return response.json()

    async def health_async(self) -> dict:
        """GET /health - Check API server health (async)."""
        response = await self._get_async_client().get("/health")
        self._handle_error(response)
        return response.json()

    # ============================================================
    # GENERATION ENDPOINTS
    # ============================================================

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        POST /api/v1/generate - Queue a new generation.

        Returns immediately with generation_id for polling.
        """
        response = self._get_sync_client().post(
            "/api/v1/generate",
            json=request.model_dump(exclude_none=True),
        )
        self._handle_error(response)
        return GenerationResponse.model_validate(response.json())

    async def generate_async(self, request: GenerationRequest) -> GenerationResponse:
        """POST /api/v1/generate - Queue a new generation (async)."""
        response = await self._get_async_client().post(
            "/api/v1/generate",
            json=request.model_dump(exclude_none=True),
        )
        self._handle_error(response)
        return GenerationResponse.model_validate(response.json())

    def get_generation_status(self, generation_id: str) -> GenerationResponse:
        """GET /api/v1/generate/{id} - Get generation status."""
        response = self._get_sync_client().get(f"/api/v1/generate/{generation_id}")
        self._handle_error(response)
        return GenerationResponse.model_validate(response.json())

    async def get_generation_status_async(
        self, generation_id: str
    ) -> GenerationResponse:
        """GET /api/v1/generate/{id} - Get generation status (async)."""
        response = await self._get_async_client().get(
            f"/api/v1/generate/{generation_id}"
        )
        self._handle_error(response)
        return GenerationResponse.model_validate(response.json())

    def cancel_generation(self, generation_id: str) -> dict:
        """DELETE /api/v1/generate/{id} - Cancel a generation."""
        response = self._get_sync_client().delete(f"/api/v1/generate/{generation_id}")
        self._handle_error(response)
        return response.json()

    async def cancel_generation_async(self, generation_id: str) -> dict:
        """DELETE /api/v1/generate/{id} - Cancel a generation (async)."""
        response = await self._get_async_client().delete(
            f"/api/v1/generate/{generation_id}"
        )
        self._handle_error(response)
        return response.json()

    # ============================================================
    # HIGH-LEVEL CONVENIENCE METHODS
    # ============================================================

    def wait_for_completion(
        self,
        generation_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> GenerationResponse:
        """
        Poll until generation completes.

        Args:
            generation_id: ID from generate() response
            poll_interval: Seconds between polls
            timeout: Maximum wait time

        Returns:
            Final GenerationResponse with image_url

        Raises:
            TimeoutError: If generation doesn't complete in time
            ComfyGenError: If generation fails
        """
        import time

        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Generation {generation_id} timed out after {timeout}s")

            status = self.get_generation_status(generation_id)

            if status.status == GenerationStatus.COMPLETED:
                return status
            elif status.status == GenerationStatus.FAILED:
                raise ComfyGenError(status.message or "Generation failed")

            time.sleep(poll_interval)

    async def wait_for_completion_async(
        self,
        generation_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> GenerationResponse:
        """Poll until generation completes (async)."""
        import time

        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Generation {generation_id} timed out after {timeout}s")

            status = await self.get_generation_status_async(generation_id)

            if status.status == GenerationStatus.COMPLETED:
                return status
            elif status.status == GenerationStatus.FAILED:
                raise ComfyGenError(status.message or "Generation failed")

            await asyncio.sleep(poll_interval)

    async def poll_status(
        self,
        generation_id: str,
        poll_interval: float = 0.5,
    ) -> AsyncIterator[GenerationResponse]:
        """
        Async generator that yields status updates.

        Usage:
            async for status in client.poll_status(gen_id):
                if status.progress:
                    print(f"{status.progress.percent:.0%} complete")
        """
        while True:
            status = await self.get_generation_status_async(generation_id)
            yield status

            if status.status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED):
                break

            await asyncio.sleep(poll_interval)

    def generate_and_wait(
        self,
        request: GenerationRequest,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> GenerationResponse:
        """
        Convenience method: queue generation and wait for result.

        Equivalent to:
            response = client.generate(request)
            return client.wait_for_completion(response.generation_id)
        """
        response = self.generate(request)
        return self.wait_for_completion(
            response.generation_id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

    async def generate_and_wait_async(
        self,
        request: GenerationRequest,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> GenerationResponse:
        """Queue generation and wait for result (async)."""
        response = await self.generate_async(request)
        return await self.wait_for_completion_async(
            response.generation_id,
            poll_interval=poll_interval,
            timeout=timeout,
        )


# Module-level convenience function
def get_client(base_url: str = "http://localhost:8000") -> ComfyGenClient:
    """Get a configured client instance."""
    return ComfyGenClient(base_url=base_url)
