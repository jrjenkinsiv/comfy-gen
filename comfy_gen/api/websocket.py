"""
WebSocket progress proxy for ComfyUI.

Proxies real-time progress updates from ComfyUI to connected clients.
"""

import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from .config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for progress updates."""

    def __init__(self):
        # Map generation_id -> list of connected clients
        self.active_connections: dict[str, list[WebSocket]] = {}
        # Map generation_id -> ComfyUI client_id
        self.comfyui_clients: dict[str, str] = {}
        # Track proxy tasks
        self.proxy_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, generation_id: str) -> None:
        """Accept a new client connection."""
        await websocket.accept()
        if generation_id not in self.active_connections:
            self.active_connections[generation_id] = []
        self.active_connections[generation_id].append(websocket)
        logger.info(f"Client connected for generation {generation_id}")

    def disconnect(self, websocket: WebSocket, generation_id: str) -> None:
        """Remove a client connection."""
        if generation_id in self.active_connections:
            if websocket in self.active_connections[generation_id]:
                self.active_connections[generation_id].remove(websocket)
            if not self.active_connections[generation_id]:
                del self.active_connections[generation_id]
                # Cancel proxy task if no clients left
                if generation_id in self.proxy_tasks:
                    self.proxy_tasks[generation_id].cancel()
                    del self.proxy_tasks[generation_id]
        logger.info(f"Client disconnected from generation {generation_id}")

    async def broadcast(self, generation_id: str, message: dict[str, Any]) -> None:
        """Send message to all clients watching a generation."""
        if generation_id not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[generation_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for dead in dead_connections:
            self.disconnect(dead, generation_id)

    def get_comfyui_client_id(self, generation_id: str) -> str:
        """Get or create ComfyUI client ID for a generation."""
        if generation_id not in self.comfyui_clients:
            self.comfyui_clients[generation_id] = str(uuid4())
        return self.comfyui_clients[generation_id]


# Global connection manager
manager = ConnectionManager()


async def proxy_comfyui_progress(generation_id: str, prompt_id: str) -> None:
    """
    Connect to ComfyUI WebSocket and proxy progress to clients.

    Args:
        generation_id: Our internal generation ID
        prompt_id: ComfyUI's prompt ID for filtering messages
    """
    client_id = manager.get_comfyui_client_id(generation_id)
    ws_url = f"ws://{settings.COMFYUI_HOST}:{settings.COMFYUI_PORT}/ws?clientId={client_id}"

    logger.info(f"Connecting to ComfyUI WebSocket: {ws_url}")

    try:
        async with websockets.connect(ws_url) as comfy_ws:
            await manager.broadcast(
                generation_id,
                {
                    "type": "connected",
                    "message": "Connected to ComfyUI progress stream",
                },
            )

            async for message in comfy_ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    # Filter by our prompt_id
                    if msg_type in ("executing", "executed", "execution_cached"):
                        msg_data = data.get("data", {})
                        if msg_data.get("prompt_id") != prompt_id:
                            continue

                    # Transform and forward relevant messages
                    if msg_type == "progress":
                        # KSampler step progress
                        progress_data = data.get("data", {})
                        await manager.broadcast(
                            generation_id,
                            {
                                "type": "progress",
                                "value": progress_data.get("value", 0),
                                "max": progress_data.get("max", 1),
                                "step": f"Step {progress_data.get('value', 0)} of {progress_data.get('max', 1)}",
                            },
                        )

                    elif msg_type == "executing":
                        # Node execution updates
                        exec_data = data.get("data", {})
                        node = exec_data.get("node")
                        if node is None:
                            # Execution complete
                            await manager.broadcast(
                                generation_id,
                                {
                                    "type": "executing",
                                    "node": None,
                                    "message": "Execution complete",
                                },
                            )
                            break
                        else:
                            await manager.broadcast(
                                generation_id,
                                {
                                    "type": "executing",
                                    "node": node,
                                    "message": f"Executing node: {node}",
                                },
                            )

                    elif msg_type == "executed":
                        # Node completed with output
                        exec_data = data.get("data", {})
                        await manager.broadcast(
                            generation_id,
                            {
                                "type": "executed",
                                "node": exec_data.get("node"),
                                "output": exec_data.get("output"),
                            },
                        )

                    elif msg_type == "execution_start":
                        await manager.broadcast(
                            generation_id,
                            {
                                "type": "start",
                                "message": "Generation started",
                            },
                        )

                    elif msg_type == "status":
                        # Queue status
                        status_data = data.get("data", {}).get("status", {})
                        await manager.broadcast(
                            generation_id,
                            {
                                "type": "status",
                                "queue_remaining": status_data.get("exec_info", {}).get("queue_remaining", 0),
                            },
                        )

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from ComfyUI: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error processing ComfyUI message: {e}")

    except ConnectionClosed:
        logger.info(f"ComfyUI WebSocket closed for generation {generation_id}")
    except Exception as e:
        logger.error(f"ComfyUI WebSocket error: {e}")
        await manager.broadcast(
            generation_id,
            {
                "type": "error",
                "message": str(e),
            },
        )


def start_progress_proxy(generation_id: str, prompt_id: str) -> None:
    """
    Start a background task to proxy progress for a generation.

    Called when a new generation is queued.
    """
    if generation_id in manager.proxy_tasks:
        return  # Already proxying

    task = asyncio.create_task(proxy_comfyui_progress(generation_id, prompt_id))
    manager.proxy_tasks[generation_id] = task


async def websocket_progress_endpoint(
    websocket: WebSocket,
    generation_id: str,
) -> None:
    """
    WebSocket endpoint handler for progress updates.

    Usage:
        ws://localhost:8000/ws/progress/{generation_id}
    """
    await manager.connect(websocket, generation_id)

    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong, disconnect)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_json({"type": "keepalive"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, generation_id)
