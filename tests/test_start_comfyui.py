"""Tests for start_comfyui.py script structure and functions.

These tests verify the script's structure without actually starting ComfyUI.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import start_comfyui  # noqa: E402


class TestStartComfyUIStructure(unittest.TestCase):
    """Test script structure and function definitions."""

    def test_constants_defined(self):
        """Verify required constants are defined."""
        self.assertTrue(hasattr(start_comfyui, "COMFYUI_PATH"))
        self.assertTrue(hasattr(start_comfyui, "PYTHON_PATH"))
        self.assertTrue(hasattr(start_comfyui, "LOG_FILE"))
        self.assertTrue(hasattr(start_comfyui, "COMFYUI_HOST"))
        self.assertTrue(hasattr(start_comfyui, "COMFYUI_PORT"))
        self.assertTrue(hasattr(start_comfyui, "COMFYUI_URL"))
        self.assertTrue(hasattr(start_comfyui, "STARTUP_TIMEOUT"))

    def test_startup_timeout_value(self):
        """Verify startup timeout is 60 seconds as required."""
        self.assertEqual(start_comfyui.STARTUP_TIMEOUT, 60)

    def test_health_check_function_exists(self):
        """Verify health check function is defined."""
        self.assertTrue(callable(start_comfyui.check_comfyui_health))

    def test_main_function_exists(self):
        """Verify main function is defined."""
        self.assertTrue(callable(start_comfyui.main))

    @patch("start_comfyui.requests.get")
    def test_check_comfyui_health_success(self, mock_get):
        """Test ComfyUI health check returns True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = start_comfyui.check_comfyui_health()
        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch("start_comfyui.requests.get")
    def test_check_comfyui_health_failure(self, mock_get):
        """Test ComfyUI health check returns False when not healthy."""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection refused")

        result = start_comfyui.check_comfyui_health()
        self.assertFalse(result)


class TestComfyUIUtils(unittest.TestCase):
    """Test comfyui_utils functions."""

    def setUp(self):
        """Import comfyui_utils before each test."""
        import comfyui_utils
        self.utils = comfyui_utils

    def test_wait_for_port_timeout(self):
        """Test wait_for_port returns False on timeout."""
        # Use a port that won't be listening
        result = self.utils.wait_for_port("127.0.0.1", 19999, timeout=1)
        self.assertFalse(result)

    @patch("socket.socket")
    def test_wait_for_port_success(self, mock_socket_class):
        """Test wait_for_port returns True when port is available."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_socket_class.return_value = mock_sock

        result = self.utils.wait_for_port("127.0.0.1", 8188, timeout=5)
        self.assertTrue(result)

    def test_read_last_n_lines_nonexistent_file(self):
        """Test read_last_n_lines returns empty list for nonexistent file."""
        result = self.utils.read_last_n_lines("/nonexistent/file.txt", 20)
        self.assertEqual(result, [])

    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\nline4\nline5\n")
    def test_read_last_n_lines_success(self, mock_file):
        """Test read_last_n_lines returns correct number of lines."""
        result = self.utils.read_last_n_lines("test.txt", 3)
        self.assertEqual(len(result), 3)
        self.assertIn("line3", result[0])
        self.assertIn("line4", result[1])
        self.assertIn("line5", result[2])

    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\n")
    def test_read_last_n_lines_fewer_than_requested(self, mock_file):
        """Test read_last_n_lines returns all lines when file has fewer than requested."""
        result = self.utils.read_last_n_lines("test.txt", 10)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
