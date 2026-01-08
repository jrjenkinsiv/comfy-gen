#!/usr/bin/env python3
"""Integration test for FastAPI generation server.

This test requires actual ComfyUI server connection.
Mark with @pytest.mark.integration to skip in CI.
"""

import sys
import time
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from api.app import app

# Create test client
client = TestClient(app)


@pytest.mark.integration
def test_full_generation_workflow():
    """Test complete generation workflow from request to completion.

    This is an integration test that requires:
    - ComfyUI server running at 192.168.1.215:8188
    - MinIO server running at 192.168.1.215:9000
    - Valid workflow file in workflows/flux-dev.json
    """
    # Check health first
    health_response = client.get("/health")
    assert health_response.status_code == 200
    health_data = health_response.json()

    if not health_data["comfyui_available"]:
        pytest.skip("ComfyUI server not available")

    # Create generation request
    request_data = {
        "prompt": "a sunset over mountains, photorealistic",
        "negative_prompt": "blurry, low quality",
        "workflow": "flux-dev.json",
        "width": 512,  # Small size for faster test
        "height": 512,
        "steps": 10,  # Few steps for faster test
        "cfg": 7.0,
        "seed": 42,
    }

    # Submit job
    create_response = client.post("/generate", json=request_data)
    assert create_response.status_code == 202
    job_data = create_response.json()
    job_id = job_data["id"]

    print(f"[INFO] Created generation job: {job_id}")

    # Poll for completion (max 5 minutes)
    max_wait = 300  # 5 minutes
    start_time = time.time()
    last_status = None

    while time.time() - start_time < max_wait:
        status_response = client.get(f"/generate/{job_id}")
        assert status_response.status_code == 200

        status_data = status_response.json()
        current_status = status_data["status"]

        # Print status updates
        if current_status != last_status:
            print(f"[INFO] Job status: {current_status} (progress: {status_data['progress']:.1%})")
            last_status = current_status

        if current_status == "completed":
            assert status_data["image_url"] is not None
            print("[OK] Generation completed successfully!")
            print(f"[OK] Image URL: {status_data['image_url']}")
            return

        elif current_status == "failed":
            error_msg = status_data.get("error", "Unknown error")
            pytest.fail(f"Generation failed: {error_msg}")

        # Wait before next poll
        time.sleep(2)

    pytest.fail("Generation timed out after 5 minutes")


if __name__ == "__main__":
    print("[INFO] Running integration test...")
    print("[INFO] This requires ComfyUI server to be running")
    test_full_generation_workflow()
