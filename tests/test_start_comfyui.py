"""Tests for start_comfyui.py script and comfyui_utils helper functions.

These tests verify the script's structure and helper functions without actually starting services.
"""

import sys
import os
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import socket
import time

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import start_comfyui
import comfyui_utils


class TestComfyUIUtilsPortChecking(unittest.TestCase):
    """Test port checking utility function."""
    
    @patch('comfyui_utils.socket.socket')
    @patch('comfyui_utils.time.sleep')
    def test_check_port_listening_success_immediate(self, mock_sleep, mock_socket_class):
        """Test port check returns True when port is listening immediately."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket
        
        result = comfyui_utils.check_port_listening("localhost", 8188, timeout=10)
        
        self.assertTrue(result)
        mock_socket.connect_ex.assert_called_once_with(("localhost", 8188))
        mock_socket.close.assert_called_once()
    
    @patch('comfyui_utils.socket.socket')
    @patch('comfyui_utils.time.sleep')
    @patch('comfyui_utils.time.time')
    def test_check_port_listening_success_after_retry(self, mock_time, mock_sleep, mock_socket_class):
        """Test port check returns True when port becomes available after retries."""
        # Simulate time passing
        mock_time.side_effect = [0, 2, 4, 6]
        
        mock_socket = MagicMock()
        # First two attempts fail, third succeeds
        mock_socket.connect_ex.side_effect = [1, 1, 0]
        mock_socket_class.return_value = mock_socket
        
        result = comfyui_utils.check_port_listening("localhost", 8188, timeout=10)
        
        self.assertTrue(result)
        self.assertEqual(mock_socket.connect_ex.call_count, 3)
    
    @patch('comfyui_utils.socket.socket')
    @patch('comfyui_utils.time.sleep')
    @patch('comfyui_utils.time.time')
    def test_check_port_listening_timeout(self, mock_time, mock_sleep, mock_socket_class):
        """Test port check returns False when timeout is exceeded."""
        # Simulate timeout after multiple attempts
        mock_time.side_effect = [0, 2, 4, 6, 8, 10, 12]
        
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1  # Always fail
        mock_socket_class.return_value = mock_socket
        
        result = comfyui_utils.check_port_listening("localhost", 8188, timeout=10)
        
        self.assertFalse(result)
    
    @patch('comfyui_utils.socket.socket')
    @patch('comfyui_utils.time.sleep')
    def test_check_port_listening_socket_error(self, mock_sleep, mock_socket_class):
        """Test port check handles socket errors gracefully."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = socket.error("Connection refused")
        mock_socket_class.return_value = mock_socket
        
        # Should not raise exception, should retry and timeout
        with patch('comfyui_utils.time.time') as mock_time:
            mock_time.side_effect = [0, 2, 4, 6, 8, 10, 12]
            result = comfyui_utils.check_port_listening("localhost", 8188, timeout=10)
        
        self.assertFalse(result)


class TestComfyUIUtilsReadLastLines(unittest.TestCase):
    """Test reading last lines from log file utility function."""
    
    def test_read_last_lines_small_file(self):
        """Test reading last lines from file smaller than requested lines."""
        file_content = "line 1\nline 2\nline 3\n"
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            result = comfyui_utils.read_last_lines("/fake/path.log", num_lines=20)
        
        self.assertEqual(result, file_content)
    
    def test_read_last_lines_exact_count(self):
        """Test reading exact number of last lines."""
        lines = [f"line {i}\n" for i in range(1, 51)]
        file_content = ''.join(lines)
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            result = comfyui_utils.read_last_lines("/fake/path.log", num_lines=20)
        
        expected = ''.join(lines[-20:])
        self.assertEqual(result, expected)
    
    def test_read_last_lines_file_not_found(self):
        """Test reading from non-existent file returns empty string."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = comfyui_utils.read_last_lines("/fake/path.log", num_lines=20)
        
        self.assertEqual(result, "")
    
    def test_read_last_lines_permission_error(self):
        """Test reading from file without permission returns empty string."""
        with patch('builtins.open', side_effect=PermissionError):
            result = comfyui_utils.read_last_lines("/fake/path.log", num_lines=20)
        
        self.assertEqual(result, "")


class TestStartComfyUIStructure(unittest.TestCase):
    """Test start_comfyui.py script structure."""
    
    def test_constants_defined(self):
        """Verify required constants are defined."""
        self.assertTrue(hasattr(start_comfyui, 'COMFYUI_PATH'))
        self.assertTrue(hasattr(start_comfyui, 'PYTHON_PATH'))
        self.assertTrue(hasattr(start_comfyui, 'LOG_FILE'))
    
    def test_main_function_exists(self):
        """Verify main function is defined."""
        self.assertTrue(callable(start_comfyui.main))


class TestStartComfyUIBehavior(unittest.TestCase):
    """Test start_comfyui.py main function behavior."""
    
    @patch('start_comfyui.check_port_listening')
    @patch('start_comfyui.subprocess.Popen')
    @patch('start_comfyui.os.chdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_main_success(self, mock_print, mock_file, mock_chdir, mock_popen, mock_port_check):
        """Test main returns 0 when port becomes available."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        mock_port_check.return_value = True
        
        result = start_comfyui.main()
        
        self.assertEqual(result, 0)
        mock_port_check.assert_called_once_with("0.0.0.0", 8188, timeout=60)
        # Verify success messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("[OK]" in str(call) for call in print_calls))
    
    @patch('start_comfyui.read_last_lines')
    @patch('start_comfyui.check_port_listening')
    @patch('start_comfyui.subprocess.Popen')
    @patch('start_comfyui.os.chdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_main_failure_timeout(self, mock_print, mock_file, mock_chdir, mock_popen, mock_port_check, mock_read_log):
        """Test main returns 1 when port doesn't become available."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        mock_port_check.return_value = False
        mock_read_log.return_value = "Error: Model not found\nTraceback...\n"
        
        result = start_comfyui.main()
        
        self.assertEqual(result, 1)
        mock_port_check.assert_called_once_with("0.0.0.0", 8188, timeout=60)
        mock_read_log.assert_called_once()
        # Verify error messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("[ERROR]" in str(call) for call in print_calls))
    
    @patch('start_comfyui.read_last_lines')
    @patch('start_comfyui.check_port_listening')
    @patch('start_comfyui.subprocess.Popen')
    @patch('start_comfyui.os.chdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_main_prints_log_on_failure(self, mock_print, mock_file, mock_chdir, mock_popen, mock_port_check, mock_read_log):
        """Test main prints last 20 lines of log on failure."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        mock_port_check.return_value = False
        
        log_content = "Last 20 lines of log\nwith errors\n"
        mock_read_log.return_value = log_content
        
        result = start_comfyui.main()
        
        self.assertEqual(result, 1)
        # Verify read_last_lines was called to get log content
        mock_read_log.assert_called_once()
        # Verify log content was printed (check individual print calls)
        printed_args = [call[0][0] if call[0] else "" for call in mock_print.call_args_list]
        self.assertIn(log_content, printed_args, "Log content should be printed on failure")
    
    @patch('start_comfyui.subprocess.Popen')
    @patch('start_comfyui.os.chdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_main_starts_subprocess_correctly(self, mock_file, mock_chdir, mock_popen):
        """Test main starts subprocess with correct arguments."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        with patch('start_comfyui.check_port_listening', return_value=True):
            start_comfyui.main()
        
        # Verify Popen was called with correct arguments
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        
        # Check command arguments
        self.assertIn("main.py", args[0])
        self.assertIn("--listen", args[0])
        self.assertIn("0.0.0.0", args[0])
        self.assertIn("--port", args[0])
        self.assertIn("8188", args[0])
        
        # Check that stderr is redirected to stdout
        self.assertEqual(kwargs.get('stderr'), sys.modules['subprocess'].STDOUT)


if __name__ == '__main__':
    unittest.main()
