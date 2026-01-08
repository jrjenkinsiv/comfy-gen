"""Tests for ComfyUI client module."""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest

from clients.comfyui_client import ComfyUIClient


class TestComfyUIClient:
    """Tests for ComfyUIClient class."""

    def test_init_default(self):
        """Test client initialization with default parameters."""
        client = ComfyUIClient()
        assert client.host == "http://192.168.1.215:8188"
        assert client.timeout == 30
        assert client._ws_url == "ws://192.168.1.215:8188/ws"

    def test_init_custom_host(self):
        """Test client initialization with custom host."""
        client = ComfyUIClient(host="http://localhost:8188", timeout=60)
        assert client.host == "http://localhost:8188"
        assert client.timeout == 60
        assert client._ws_url == "ws://localhost:8188/ws"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from host."""
        client = ComfyUIClient(host="http://192.168.1.215:8188/")
        assert client.host == "http://192.168.1.215:8188"

    @patch('clients.comfyui_client.requests.get')
    def test_check_availability_success(self, mock_get):
        """Test check_availability returns True when server is up."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = ComfyUIClient()
        assert client.check_availability() is True
        mock_get.assert_called_once_with(
            "http://192.168.1.215:8188/system_stats",
            timeout=5
        )

    @patch('clients.comfyui_client.requests.get')
    def test_check_availability_connection_error(self, mock_get):
        """Test check_availability returns False on connection error."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        client = ComfyUIClient()
        assert client.check_availability() is False

    @patch('clients.comfyui_client.requests.get')
    def test_check_availability_timeout(self, mock_get):
        """Test check_availability returns False on timeout."""
        import requests
        mock_get.side_effect = requests.Timeout("Timeout")

        client = ComfyUIClient()
        assert client.check_availability() is False

    @patch('clients.comfyui_client.requests.get')
    def test_get_system_stats_success(self, mock_get):
        """Test get_system_stats returns stats when successful."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "system": {"ram": {"total": 32000}},
            "devices": [{"name": "NVIDIA RTX 5090", "vram_total": 32000}]
        }
        mock_get.return_value = mock_response

        client = ComfyUIClient()
        stats = client.get_system_stats()
        
        assert stats is not None
        assert "system" in stats
        assert "devices" in stats
        mock_get.assert_called_once()

    @patch('clients.comfyui_client.requests.get')
    def test_get_system_stats_failure(self, mock_get):
        """Test get_system_stats returns None on failure."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        client = ComfyUIClient()
        stats = client.get_system_stats()
        
        assert stats is None

    @patch('clients.comfyui_client.requests.get')
    def test_get_available_models_success(self, mock_get):
        """Test get_available_models extracts checkpoints and LoRAs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "CheckpointLoaderSimple": {
                "input": {
                    "required": {
                        "ckpt_name": [["model1.safetensors", "model2.ckpt"]]
                    }
                }
            },
            "LoraLoader": {
                "input": {
                    "required": {
                        "lora_name": [["lora1.safetensors", "lora2.safetensors"]]
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        client = ComfyUIClient()
        models = client.get_available_models()
        
        assert models is not None
        assert "checkpoints" in models
        assert "loras" in models
        assert "model1.safetensors" in models["checkpoints"]
        assert "model2.ckpt" in models["checkpoints"]
        assert "lora1.safetensors" in models["loras"]

    @patch('clients.comfyui_client.requests.get')
    def test_get_available_models_empty(self, mock_get):
        """Test get_available_models handles empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        client = ComfyUIClient()
        models = client.get_available_models()
        
        assert models is not None
        assert models.get("checkpoints", []) == []
        assert models.get("loras", []) == []

    @patch('clients.comfyui_client.requests.post')
    def test_queue_prompt_success(self, mock_post):
        """Test queue_prompt successfully queues workflow."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "prompt_id": "test-prompt-id-12345"
        }
        mock_post.return_value = mock_response

        workflow = {"nodes": [{"id": 1, "type": "test"}]}
        
        client = ComfyUIClient()
        result = client.queue_prompt(workflow)
        
        assert result is not None
        assert "prompt_id" in result
        assert result["prompt_id"] == "test-prompt-id-12345"
        
        # Verify POST was called with correct data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "json" in call_args.kwargs
        assert "prompt" in call_args.kwargs["json"]

    @patch('clients.comfyui_client.requests.post')
    def test_queue_prompt_failure(self, mock_post):
        """Test queue_prompt handles errors gracefully."""
        import requests
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        workflow = {"nodes": [{"id": 1}]}
        
        client = ComfyUIClient()
        result = client.queue_prompt(workflow)
        
        assert result is None

    @patch('clients.comfyui_client.requests.get')
    def test_get_history_success(self, mock_get):
        """Test get_history retrieves prompt history."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "prompt-id-123": {
                "outputs": {"node_1": {"images": [{"filename": "test.png"}]}}
            }
        }
        mock_get.return_value = mock_response

        client = ComfyUIClient()
        history = client.get_history("prompt-id-123")
        
        assert history is not None
        assert "prompt-id-123" in history
        assert "outputs" in history["prompt-id-123"]

    @patch('clients.comfyui_client.requests.get')
    def test_get_image_success(self, mock_get):
        """Test get_image downloads image data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake-image-data"
        mock_get.return_value = mock_response

        client = ComfyUIClient()
        image_data = client.get_image("test.png")
        
        assert image_data == b"fake-image-data"
        mock_get.assert_called_once()

    @patch('clients.comfyui_client.requests.get')
    def test_get_image_not_found(self, mock_get):
        """Test get_image returns None for 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = ComfyUIClient()
        image_data = client.get_image("nonexistent.png")
        
        assert image_data is None
