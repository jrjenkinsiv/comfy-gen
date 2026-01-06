"""Tests for start_all_services.py script structure and functions.

These tests verify the script's structure without actually starting services.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import start_all_services  # noqa: E402


class TestStartAllServicesStructure(unittest.TestCase):
    """Test script structure and function definitions."""

    def test_constants_defined(self):
        """Verify required constants are defined."""
        self.assertTrue(hasattr(start_all_services, "COMFYUI_PATH"))
        self.assertTrue(hasattr(start_all_services, "COMFYUI_PYTHON"))
        self.assertTrue(hasattr(start_all_services, "COMFYUI_URL"))
        self.assertTrue(hasattr(start_all_services, "MINIO_EXE"))
        self.assertTrue(hasattr(start_all_services, "MINIO_URL"))

    def test_health_check_functions_exist(self):
        """Verify health check functions are defined."""
        self.assertTrue(callable(start_all_services.check_comfyui_health))
        self.assertTrue(callable(start_all_services.check_minio_health))

    def test_service_start_functions_exist(self):
        """Verify service start functions are defined."""
        self.assertTrue(callable(start_all_services.start_comfyui))
        self.assertTrue(callable(start_all_services.start_minio))

    def test_status_function_exists(self):
        """Verify status check function is defined."""
        self.assertTrue(callable(start_all_services.check_status))

    @patch("start_all_services.requests.get")
    def test_check_comfyui_health_success(self, mock_get):
        """Test ComfyUI health check returns True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = start_all_services.check_comfyui_health()
        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch("start_all_services.requests.get")
    def test_check_comfyui_health_failure(self, mock_get):
        """Test ComfyUI health check returns False when not healthy."""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection refused")

        result = start_all_services.check_comfyui_health()
        self.assertFalse(result)

    @patch("start_all_services.requests.get")
    def test_check_minio_health_success(self, mock_get):
        """Test MinIO health check returns True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = start_all_services.check_minio_health()
        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch("start_all_services.requests.get")
    def test_check_minio_health_failure(self, mock_get):
        """Test MinIO health check returns False when not healthy."""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection refused")

        result = start_all_services.check_minio_health()
        self.assertFalse(result)

    @patch("start_all_services.check_comfyui_health")
    def test_start_comfyui_already_running(self, mock_health):
        """Test start_comfyui returns True if already running."""
        mock_health.return_value = True

        result = start_all_services.start_comfyui()
        self.assertTrue(result)

    @patch("start_all_services.check_minio_health")
    def test_start_minio_already_running(self, mock_health):
        """Test start_minio returns True if already running."""
        mock_health.return_value = True

        result = start_all_services.start_minio()
        self.assertTrue(result)

    @patch("start_all_services.check_comfyui_health")
    @patch("start_all_services.check_minio_health")
    @patch("builtins.print")
    def test_check_status_all_healthy(self, mock_print, mock_minio, mock_comfyui):
        """Test check_status returns True when all services healthy."""
        mock_comfyui.return_value = True
        mock_minio.return_value = True

        result = start_all_services.check_status()
        self.assertTrue(result)

    @patch("start_all_services.check_comfyui_health")
    @patch("start_all_services.check_minio_health")
    @patch("builtins.print")
    def test_check_status_one_unhealthy(self, mock_print, mock_minio, mock_comfyui):
        """Test check_status returns False when one service unhealthy."""
        mock_comfyui.return_value = True
        mock_minio.return_value = False

        result = start_all_services.check_status()
        self.assertFalse(result)


class TestWindowsProcessFlags(unittest.TestCase):
    """Test Windows process creation flags are properly defined."""

    def test_process_flags_defined(self):
        """Verify Windows process flags are defined correctly."""
        self.assertEqual(start_all_services.DETACHED_PROCESS, 0x00000008)
        self.assertEqual(start_all_services.CREATE_NEW_PROCESS_GROUP, 0x00000200)
        self.assertEqual(start_all_services.CREATE_NO_WINDOW, 0x08000000)


if __name__ == "__main__":
    unittest.main()
