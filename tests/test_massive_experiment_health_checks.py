"""Tests for massive_experiment_framework.py health check functions.

These tests verify health check functionality without actually connecting to services.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import massive_experiment_framework


class TestHealthCheckFunctions(unittest.TestCase):
    """Test health check functions."""
    
    def test_health_check_constants_defined(self):
        """Verify health check constants are defined."""
        self.assertTrue(hasattr(massive_experiment_framework, 'COMFYUI_URL'))
        self.assertTrue(hasattr(massive_experiment_framework, 'MINIO_URL'))
        self.assertTrue(hasattr(massive_experiment_framework, 'HEALTH_CHECK_TIMEOUT'))
        self.assertTrue(hasattr(massive_experiment_framework, 'HEALTH_CHECK_RETRIES'))
        self.assertTrue(hasattr(massive_experiment_framework, 'HEALTH_CHECK_RETRY_DELAY'))
        self.assertTrue(hasattr(massive_experiment_framework, 'PERIODIC_CHECK_INTERVAL'))
    
    def test_health_check_functions_exist(self):
        """Verify health check functions are defined."""
        self.assertTrue(callable(massive_experiment_framework.check_comfyui_health))
        self.assertTrue(callable(massive_experiment_framework.check_minio_health))
        self.assertTrue(callable(massive_experiment_framework.run_health_checks_with_retry))
        self.assertTrue(callable(massive_experiment_framework.log_health_check_to_mlflow))
    
    @patch('massive_experiment_framework.requests.get')
    def test_check_comfyui_health_success(self, mock_get):
        """Test ComfyUI health check returns True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = massive_experiment_framework.check_comfyui_health()
        self.assertTrue(result)
        mock_get.assert_called_once()
        
        # Verify correct endpoint
        call_args = mock_get.call_args
        self.assertIn('/system_stats', call_args[0][0])
    
    @patch('massive_experiment_framework.requests.get')
    def test_check_comfyui_health_failure(self, mock_get):
        """Test ComfyUI health check returns False when not healthy."""
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("Connection refused")
        
        result = massive_experiment_framework.check_comfyui_health()
        self.assertFalse(result)
    
    @patch('massive_experiment_framework.requests.get')
    def test_check_minio_health_success(self, mock_get):
        """Test MinIO health check returns True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = massive_experiment_framework.check_minio_health()
        self.assertTrue(result)
        mock_get.assert_called_once()
        
        # Verify correct endpoint
        call_args = mock_get.call_args
        self.assertIn('/minio/health/live', call_args[0][0])
    
    @patch('massive_experiment_framework.requests.get')
    def test_check_minio_health_failure(self, mock_get):
        """Test MinIO health check returns False when not healthy."""
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("Connection refused")
        
        result = massive_experiment_framework.check_minio_health()
        self.assertFalse(result)
    
    @patch('massive_experiment_framework.check_comfyui_health')
    @patch('massive_experiment_framework.check_minio_health')
    @patch('builtins.print')
    def test_run_health_checks_with_retry_all_healthy(self, mock_print, mock_minio, mock_comfyui):
        """Test health check with retry succeeds when all services healthy."""
        mock_comfyui.return_value = True
        mock_minio.return_value = True
        
        success, message = massive_experiment_framework.run_health_checks_with_retry()
        
        self.assertTrue(success)
        self.assertEqual(message, "All services healthy")
        # Should only call once if healthy on first attempt
        self.assertEqual(mock_comfyui.call_count, 1)
        self.assertEqual(mock_minio.call_count, 1)
    
    @patch('massive_experiment_framework.check_comfyui_health')
    @patch('massive_experiment_framework.check_minio_health')
    @patch('massive_experiment_framework.time.sleep')
    @patch('builtins.print')
    def test_run_health_checks_with_retry_fails_after_retries(
        self, mock_print, mock_sleep, mock_minio, mock_comfyui
    ):
        """Test health check with retry fails after all retries exhausted."""
        mock_comfyui.return_value = False
        mock_minio.return_value = True
        
        success, message = massive_experiment_framework.run_health_checks_with_retry()
        
        self.assertFalse(success)
        self.assertIn("ComfyUI", message)
        # Should retry HEALTH_CHECK_RETRIES times
        self.assertEqual(mock_comfyui.call_count, massive_experiment_framework.HEALTH_CHECK_RETRIES)
        # Should sleep between retries (but not after last one)
        self.assertEqual(mock_sleep.call_count, massive_experiment_framework.HEALTH_CHECK_RETRIES - 1)
    
    @patch('massive_experiment_framework.check_comfyui_health')
    @patch('massive_experiment_framework.check_minio_health')
    @patch('massive_experiment_framework.time.sleep')
    @patch('builtins.print')
    def test_run_health_checks_with_retry_recovers_on_second_attempt(
        self, mock_print, mock_sleep, mock_minio, mock_comfyui
    ):
        """Test health check with retry succeeds on second attempt."""
        # First call fails, second succeeds
        mock_comfyui.side_effect = [False, True, True]
        mock_minio.return_value = True
        
        success, message = massive_experiment_framework.run_health_checks_with_retry()
        
        self.assertTrue(success)
        self.assertEqual(message, "All services healthy")
        # Should call twice (fail, then succeed)
        self.assertEqual(mock_comfyui.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)
    
    @patch('massive_experiment_framework.mlflow.set_tag')
    @patch('massive_experiment_framework.mlflow.log_metric')
    def test_log_health_check_to_mlflow_success(self, mock_log_metric, mock_set_tag):
        """Test logging successful health check to MLflow."""
        massive_experiment_framework.log_health_check_to_mlflow(True, "All good")
        
        # Should log tags and metrics
        self.assertEqual(mock_set_tag.call_count, 2)
        mock_log_metric.assert_called_once_with("services_healthy", 1)
    
    @patch('massive_experiment_framework.mlflow.set_tag')
    @patch('massive_experiment_framework.mlflow.log_metric')
    def test_log_health_check_to_mlflow_failure(self, mock_log_metric, mock_set_tag):
        """Test logging failed health check to MLflow."""
        massive_experiment_framework.log_health_check_to_mlflow(False, "Service down")
        
        # Should log tags and metrics
        self.assertEqual(mock_set_tag.call_count, 2)
        mock_log_metric.assert_called_once_with("services_healthy", 0)


if __name__ == '__main__':
    unittest.main()
