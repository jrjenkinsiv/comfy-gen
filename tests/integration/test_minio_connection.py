"""Integration tests for MinIO connectivity."""

import pytest

from clients.minio_client import MinIOClient


@pytest.mark.integration
class TestMinIOIntegration:
    """Integration tests for MinIO server (requires real service)."""

    def test_minio_server_reachable(self):
        """Test that MinIO server at moira:9000 is reachable."""
        client = MinIOClient(endpoint="192.168.1.215:9000")

        # Try to ensure bucket exists (tests connectivity)
        try:
            client._ensure_bucket()
            # If no exception, server is reachable
            assert True
        except Exception as e:
            pytest.fail(f"MinIO server not reachable at moira:9000: {e}")

    def test_list_objects(self):
        """Test listing objects in MinIO bucket."""
        client = MinIOClient(endpoint="192.168.1.215:9000", bucket="comfy-gen")

        # Try to list objects (tests connectivity and bucket access)
        try:
            objects = client.list_objects()
            # Should return a list (may be empty)
            assert isinstance(objects, list)
        except Exception as e:
            pytest.fail(f"Failed to list MinIO objects: {e}")

    def test_get_object_url(self):
        """Test generating object URL."""
        client = MinIOClient(endpoint="192.168.1.215:9000", bucket="comfy-gen")

        url = client.get_object_url("test.png")

        # Should generate valid URL
        assert "192.168.1.215:9000" in url
        assert "comfy-gen" in url
        assert "test.png" in url
