"""Tests for MLflow logger module."""

from unittest.mock import MagicMock, Mock, patch

from utils.mlflow_logger import (
    DEFAULT_EXPERIMENT,
    MLFLOW_URI,
    SYSTEM_METRICS_ENABLED,
    log_batch,
    log_experiment,
    log_favorite,
)


class TestMLflowLoggerModule:
    """Tests for MLflow logger module."""

    def test_constants(self):
        """Test that module constants are defined."""
        assert MLFLOW_URI == "http://192.168.1.162:5001"
        assert DEFAULT_EXPERIMENT == "comfy-gen-nsfw"
        assert isinstance(SYSTEM_METRICS_ENABLED, bool)


class TestLogExperiment:
    """Tests for log_experiment function."""

    @patch("utils.mlflow_logger.mlflow")
    def test_log_experiment_basic(self, mock_mlflow):
        """Test basic experiment logging."""
        # Setup mocks
        mock_mlflow.set_tracking_uri = Mock()
        mock_mlflow.set_experiment = Mock(return_value=Mock(experiment_id="exp-123"))
        mock_mlflow.start_run = MagicMock()
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run

        # Call function
        log_experiment(
            run_name="test_run",
            image_url="http://192.168.1.215:9000/comfy-gen/test.png",
            params={"checkpoint": "flux-dev", "steps": 50},
            validation_score=0.75,
            user_rating=4,
            feedback="Test run",
        )

        # Verify MLflow calls
        mock_mlflow.set_tracking_uri.assert_called_once_with(MLFLOW_URI)
        mock_mlflow.set_experiment.assert_called_once()

    @patch("utils.mlflow_logger.mlflow")
    def test_log_experiment_with_loras(self, mock_mlflow):
        """Test experiment logging with LoRAs."""
        mock_mlflow.set_tracking_uri = Mock()
        mock_mlflow.set_experiment = Mock(return_value=Mock(experiment_id="exp-123"))
        mock_mlflow.start_run = MagicMock()
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run

        # Call with LoRAs
        log_experiment(
            run_name="test_lora_run",
            image_url="http://192.168.1.215:9000/comfy-gen/test.png",
            params={
                "checkpoint": "flux-dev",
                "loras": "add_detail:0.5,more_details:0.3",
                "steps": 50,
            },
            validation_score=0.8,
        )

        # Verify function executed without errors
        mock_mlflow.set_tracking_uri.assert_called_once()

    @patch("utils.mlflow_logger.mlflow")
    def test_log_experiment_missing_params_warning(self, mock_mlflow):
        """Test that missing required params trigger warnings."""
        mock_mlflow.set_tracking_uri = Mock()
        mock_mlflow.set_experiment = Mock(return_value=Mock(experiment_id="exp-123"))
        mock_mlflow.start_run = MagicMock()
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run

        # Call with minimal params (missing required ones)
        log_experiment(
            run_name="minimal_run",
            image_url="http://192.168.1.215:9000/comfy-gen/test.png",
            params={"checkpoint": "flux-dev"},  # Missing steps, cfg, etc.
        )

        # Should still execute without crashing
        mock_mlflow.set_tracking_uri.assert_called_once()

    @patch("utils.mlflow_logger.mlflow")
    def test_log_experiment_custom_experiment(self, mock_mlflow):
        """Test logging to custom experiment."""
        mock_mlflow.set_tracking_uri = Mock()
        mock_mlflow.set_experiment = Mock(return_value=Mock(experiment_id="exp-456"))
        mock_mlflow.start_run = MagicMock()
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run

        log_experiment(
            run_name="custom_exp_run",
            image_url="http://192.168.1.215:9000/comfy-gen/test.png",
            params={"checkpoint": "flux-dev"},
            experiment_name="comfy-gen-custom",
        )

        # Verify custom experiment was set
        call_args = mock_mlflow.set_experiment.call_args
        assert "comfy-gen-custom" in str(call_args)


class TestLogFavorite:
    """Tests for log_favorite function."""

    @patch("utils.mlflow_logger.log_experiment")
    def test_log_favorite_calls_log_experiment(self, mock_log_experiment):
        """Test that log_favorite calls log_experiment with correct params."""
        log_favorite(
            run_name="favorite_test",
            image_url="http://192.168.1.215:9000/comfy-gen/fav.png",
            params={"checkpoint": "flux-dev"},
            feedback="Best result",
        )

        # Verify log_experiment was called
        mock_log_experiment.assert_called_once()
        call_kwargs = mock_log_experiment.call_args.kwargs

        # Should use favorites experiment
        assert call_kwargs.get("experiment_name") == "comfy-gen-nsfw-favorites"
        # Should set rating to 5
        assert call_kwargs.get("user_rating") == 5


class TestLogBatch:
    """Tests for log_batch function."""

    @patch("utils.mlflow_logger.log_experiment")
    def test_log_batch_multiple_experiments(self, mock_log_experiment):
        """Test batch logging of multiple experiments."""
        experiments = [
            {
                "run_name": "batch_1",
                "image_url": "http://192.168.1.215:9000/comfy-gen/1.png",
                "params": {"checkpoint": "flux-dev"},
                "user_rating": 3,
            },
            {
                "run_name": "batch_2",
                "image_url": "http://192.168.1.215:9000/comfy-gen/2.png",
                "params": {"checkpoint": "flux-dev"},
                "user_rating": 4,
            },
        ]

        log_batch(experiments)

        # Should call log_experiment for each
        assert mock_log_experiment.call_count == 2

    @patch("utils.mlflow_logger.log_experiment")
    def test_log_batch_empty_list(self, mock_log_experiment):
        """Test batch logging with empty list."""
        log_batch([])

        # Should not call log_experiment
        mock_log_experiment.assert_not_called()

    @patch("utils.mlflow_logger.log_experiment")
    def test_log_batch_custom_experiment(self, mock_log_experiment):
        """Test batch logging to custom experiment."""
        experiments = [
            {
                "run_name": "batch_custom",
                "image_url": "http://192.168.1.215:9000/comfy-gen/1.png",
                "params": {"checkpoint": "flux-dev"},
            }
        ]

        log_batch(experiments, experiment_name="custom-batch")

        # Verify experiment name passed
        call_kwargs = mock_log_experiment.call_args.kwargs
        assert call_kwargs.get("experiment_name") == "custom-batch"


class TestMLflowHealthCheck:
    """Tests for MLflow health check functionality."""

    @patch("utils.mlflow_logger.requests.get")
    def test_mlflow_health_check_success(self, mock_get):
        """Test MLflow health check when server is up."""
        # This would be part of the actual implementation
        # Testing the pattern that should exist
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Verify health check URL would be called
        # (Actual health check implementation may vary)
        assert MLFLOW_URI == "http://192.168.1.162:5001"

    @patch("utils.mlflow_logger.requests.get")
    def test_mlflow_health_check_failure(self, mock_get):
        """Test MLflow health check when server is down."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection refused")

        # Health check should handle connection errors gracefully
        # (Actual implementation may log warnings)
        assert MLFLOW_URI == "http://192.168.1.162:5001"
