#!/usr/bin/env python3
"""Unit tests for FastAPI generation server."""

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import app
from api.services.generation import GenerationService

# Create test client
client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    with patch("clients.comfyui_client.ComfyUIClient.check_availability") as mock_check:
        mock_check.return_value = True

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["comfyui_available"] is True
        assert "version" in data

        print("[OK] Health endpoint returns correct status when ComfyUI is available")


def test_health_endpoint_degraded():
    """Test health endpoint when ComfyUI is unavailable."""
    with patch("clients.comfyui_client.ComfyUIClient.check_availability") as mock_check:
        mock_check.return_value = False

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["comfyui_available"] is False

        print("[OK] Health endpoint shows degraded status when ComfyUI is unavailable")


def test_create_generation_success():
    """Test creating a generation job."""
    request_data = {
        "prompt": "a beautiful landscape",
        "negative_prompt": "blurry",
        "workflow": "flux-dev.json",
        "width": 1024,
        "height": 1024,
        "steps": 20,
        "cfg": 7.0,
        "seed": 42,
    }

    with patch("api.services.generation.GenerationService._execute_job"):
        response = client.post("/generate", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert data["status"] == "queued"
        assert data["progress"] == 0.0

        print("[OK] Create generation endpoint returns job ID and queued status")


def test_create_generation_validation_error():
    """Test validation error for invalid dimensions."""
    request_data = {
        "prompt": "test",
        "width": 1023,  # Not divisible by 8
        "height": 1024,
    }

    response = client.post("/generate", json=request_data)
    assert response.status_code == 422  # Validation error

    print("[OK] Create generation validates dimensions are divisible by 8")


def test_get_generation_status():
    """Test getting generation status."""
    # Create a job first
    request_data = {"prompt": "test prompt"}

    with patch("api.services.generation.GenerationService._execute_job"):
        create_response = client.post("/generate", json=request_data)
        job_id = create_response.json()["id"]

        # Get status
        response = client.get(f"/generate/{job_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == job_id
        assert "status" in data
        assert "progress" in data

        print("[OK] Get generation status returns job details")


def test_get_generation_not_found():
    """Test getting non-existent job."""
    response = client.get("/generate/nonexistent-job-id")
    assert response.status_code == 404

    print("[OK] Get generation returns 404 for non-existent job")


def test_generation_service_create_job():
    """Test GenerationService creates jobs correctly."""
    service = GenerationService()

    with patch.object(service, "_execute_job"):
        job_id = service.create_job(
            prompt="test prompt",
            negative_prompt="bad quality",
            workflow="flux-dev.json",
            width=1024,
            height=1024,
            steps=20,
            cfg=7.0,
            seed=42,
        )

        assert job_id is not None
        job = service.get_job(job_id)
        assert job is not None
        assert job.prompt == "test prompt"
        assert job.status == "queued"

        print("[OK] GenerationService creates and stores jobs")


def test_generation_service_job_not_found():
    """Test getting non-existent job from service."""
    service = GenerationService()
    job = service.get_job("nonexistent-id")
    assert job is None

    print("[OK] GenerationService returns None for non-existent job")


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "ComfyGen API"
    assert "version" in data
    assert data["status"] == "running"

    print("[OK] Root endpoint returns API info")


if __name__ == "__main__":
    # Run tests
    test_health_endpoint()
    test_health_endpoint_degraded()
    test_create_generation_success()
    test_create_generation_validation_error()
    test_get_generation_status()
    test_get_generation_not_found()
    test_generation_service_create_job()
    test_generation_service_job_not_found()
    test_root_endpoint()

    print("\n[OK] All API unit tests passed!")
