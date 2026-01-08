"""Integration test for simple image generation."""

import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestSimpleGeneration:
    """End-to-end test for simple image generation (requires real services)."""

    def test_simple_sd15_generation(self):
        """Test simple SD 1.5 generation workflow.

        Note: This test requires:
        - ComfyUI server running on moira:8188
        - A valid SD 1.5 checkpoint available
        - MinIO server running on moira:9000

        This is a minimal smoke test to verify the full pipeline works.
        """
        pytest.skip("Requires manual execution with valid checkpoint - too slow for CI")

    def test_workflow_validation(self):
        """Test that workflow JSON files are valid."""
        import json
        from pathlib import Path

        workflows_dir = Path(__file__).parent.parent.parent / "workflows"

        # Check that workflows directory exists
        assert workflows_dir.exists(), "workflows/ directory not found"

        # Find all JSON workflow files
        workflow_files = list(workflows_dir.glob("*.json"))
        assert len(workflow_files) > 0, "No workflow JSON files found"

        # Validate each workflow is valid JSON
        for workflow_file in workflow_files:
            with open(workflow_file) as f:
                try:
                    data = json.load(f)
                    assert isinstance(data, dict), f"{workflow_file.name} is not a JSON object"
                except json.JSONDecodeError as e:
                    pytest.fail(f"{workflow_file.name} is not valid JSON: {e}")

    def test_comfyui_and_minio_both_reachable(self):
        """Test that both ComfyUI and MinIO are reachable for generation."""
        from clients.comfyui_client import ComfyUIClient
        from clients.minio_client import MinIOClient

        # Test ComfyUI
        comfyui = ComfyUIClient(host="http://192.168.1.215:8188")
        assert comfyui.check_availability(), "ComfyUI not reachable"

        # Test MinIO
        minio = MinIOClient(endpoint="192.168.1.215:9000")
        try:
            minio._ensure_bucket()
            minio_ok = True
        except Exception:
            minio_ok = False

        assert minio_ok, "MinIO not reachable"
