"""Integration tests for MLflow connectivity."""

import pytest


@pytest.mark.integration
class TestMLflowIntegration:
    """Integration tests for MLflow server (requires real service)."""

    def test_mlflow_server_reachable(self):
        """Test that MLflow server at cerebro:5001 is reachable."""
        import requests

        try:
            response = requests.get("http://192.168.1.162:5001", timeout=5)
            # MLflow may return 200 or redirect, just check it responds
            assert response.status_code in [200, 302, 404], f"Unexpected status: {response.status_code}"
        except requests.ConnectionError:
            pytest.fail("MLflow server not reachable at cerebro:5001")

    def test_mlflow_api_endpoint(self):
        """Test MLflow API endpoint responds."""
        import requests

        try:
            # Try to access experiments endpoint
            response = requests.get("http://192.168.1.162:5001/api/2.0/mlflow/experiments/list", timeout=5)

            # Should get a valid response (200 or auth required)
            assert response.status_code in [200, 401, 403], f"API endpoint failed: {response.status_code}"
        except requests.ConnectionError:
            pytest.fail("MLflow API endpoint not accessible")

    def test_mlflow_tracking_uri(self):
        """Test MLflow tracking URI configuration."""
        from utils.mlflow_logger import MLFLOW_URI

        assert MLFLOW_URI == "http://192.168.1.162:5001"

    def test_mlflow_can_set_tracking_uri(self):
        """Test that mlflow can set tracking URI."""
        import mlflow

        try:
            mlflow.set_tracking_uri("http://192.168.1.162:5001")
            # If no exception, configuration worked
            assert True
        except Exception as e:
            pytest.fail(f"Failed to set MLflow tracking URI: {e}")
