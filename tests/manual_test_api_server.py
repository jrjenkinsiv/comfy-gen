#!/usr/bin/env python3
"""Manual test script for FastAPI generation server.

Usage:
    1. Start the server: python3 api/app.py
    2. Run this script: python3 tests/manual_test_api_server.py
"""

import sys
import time
from pathlib import Path

import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

API_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("\n[TEST] Health check...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("[OK] Health check passed")


def test_root():
    """Test root endpoint."""
    print("\n[TEST] Root endpoint...")
    response = requests.get(f"{API_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("[OK] Root endpoint passed")


def test_generation():
    """Test generation workflow."""
    print("\n[TEST] Generation workflow...")

    # Create generation request
    request_data = {
        "prompt": "a sunset over mountains, photorealistic",
        "negative_prompt": "blurry, low quality",
        "workflow": "flux-dev.json",
        "width": 512,  # Small for quick test
        "height": 512,
        "steps": 10,  # Few steps for quick test
        "cfg": 7.0,
        "seed": 42,
    }

    print(f"Request: {request_data}")
    response = requests.post(f"{API_URL}/generate", json=request_data)
    print(f"Status: {response.status_code}")

    if response.status_code != 202:
        print(f"[ERROR] Unexpected status code: {response.status_code}")
        print(f"Response: {response.text}")
        return

    data = response.json()
    job_id = data["id"]
    print(f"Job ID: {job_id}")
    print("[OK] Generation request submitted")

    # Poll for completion
    print("\n[TEST] Polling for completion...")
    max_wait = 300  # 5 minutes
    start_time = time.time()
    last_status = None

    while time.time() - start_time < max_wait:
        response = requests.get(f"{API_URL}/generate/{job_id}")
        if response.status_code != 200:
            print(f"[ERROR] Status check failed: {response.status_code}")
            break

        status_data = response.json()
        current_status = status_data["status"]

        if current_status != last_status:
            print(f"Status: {current_status} (progress: {status_data['progress']:.1%})")
            last_status = current_status

        if current_status == "completed":
            print(f"[OK] Generation completed!")
            print(f"Image URL: {status_data['image_url']}")
            return

        elif current_status == "failed":
            print(f"[ERROR] Generation failed: {status_data.get('error')}")
            return

        time.sleep(2)

    print("[ERROR] Generation timed out")


if __name__ == "__main__":
    print("=" * 60)
    print("FastAPI Generation Server Manual Test")
    print("=" * 60)
    print("\nMake sure the server is running:")
    print("  python3 api/app.py")
    print()

    try:
        test_health()
        test_root()
        test_generation()

        print("\n" + "=" * 60)
        print("[OK] All manual tests completed!")
        print("=" * 60)

    except requests.ConnectionError:
        print("\n[ERROR] Cannot connect to server at", API_URL)
        print("Make sure the server is running: python3 api/app.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
