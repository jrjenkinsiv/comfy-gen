"""Tests for MinIO client module."""

import io
from unittest.mock import Mock, patch

from clients.minio_client import MinIOClient


class TestMinIOClient:
    """Tests for MinIOClient class."""

    def test_init_default(self):
        """Test client initialization with default parameters."""
        client = MinIOClient()
        assert client.endpoint == "192.168.1.215:9000"
        assert client.bucket == "comfy-gen"
        assert client.client is not None

    def test_init_custom_params(self):
        """Test client initialization with custom parameters."""
        client = MinIOClient(
            endpoint="localhost:9000", access_key="testkey", secret_key="testsecret", bucket="test-bucket", secure=True
        )
        assert client.endpoint == "localhost:9000"
        assert client.bucket == "test-bucket"

    @patch("clients.minio_client.Minio")
    def test_init_uses_env_credentials(self, mock_minio):
        """Test that client uses environment variables for credentials."""
        with patch.dict("os.environ", {"MINIO_ACCESS_KEY": "env_access", "MINIO_SECRET_KEY": "env_secret"}):
            MinIOClient()

            # Verify Minio was called with env credentials
            mock_minio.assert_called_once()
            call_kwargs = mock_minio.call_args.kwargs
            assert call_kwargs.get("access_key") == "env_access"
            assert call_kwargs.get("secret_key") == "env_secret"

    def test_ensure_bucket_called_lazily(self):
        """Test that bucket existence check is deferred."""
        with patch("clients.minio_client.Minio"):
            client = MinIOClient()
            # Should not check bucket on init
            assert client._bucket_checked is False

    @patch.object(MinIOClient, "_ensure_bucket")
    def test_upload_file_ensures_bucket(self, mock_ensure):
        """Test that upload_file calls _ensure_bucket."""
        with patch("clients.minio_client.Minio"):
            client = MinIOClient()
            client.client.fput_object = Mock()

            client.upload_file("/tmp/test.png", "test.png")

            # Should ensure bucket exists
            mock_ensure.assert_called_once()

    def test_upload_file_success(self):
        """Test successful file upload."""
        with patch("clients.minio_client.Minio") as mock_minio_class:
            mock_client = Mock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = True

            client = MinIOClient()
            client._ensure_bucket()

            # Mock successful upload
            mock_client.fput_object.return_value = Mock(object_name="test.png")

            result = client.upload_file("/tmp/test.png", "test.png")

            assert result is True
            mock_client.fput_object.assert_called_once()

    def test_upload_file_creates_bucket_if_missing(self):
        """Test that upload creates bucket if it doesn't exist."""
        with patch("clients.minio_client.Minio") as mock_minio_class:
            mock_client = Mock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = False

            client = MinIOClient()
            client._ensure_bucket()

            # Should create bucket
            mock_client.make_bucket.assert_called_once_with(client.bucket)

    def test_download_file_success(self):
        """Test successful file download."""
        with patch("clients.minio_client.Minio") as mock_minio_class:
            mock_client = Mock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = True

            client = MinIOClient()
            client._ensure_bucket()

            client.download_file("test.png", "/tmp/downloaded.png")

            mock_client.fget_object.assert_called_once_with(client.bucket, "test.png", "/tmp/downloaded.png")

    def test_list_objects_success(self):
        """Test listing objects in bucket."""
        with patch("clients.minio_client.Minio") as mock_minio_class:
            mock_client = Mock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = True

            # Mock list_objects response
            mock_obj1 = Mock()
            mock_obj1.object_name = "file1.png"
            mock_obj2 = Mock()
            mock_obj2.object_name = "file2.png"
            mock_client.list_objects.return_value = [mock_obj1, mock_obj2]

            client = MinIOClient()
            client._ensure_bucket()

            objects = client.list_objects()

            assert len(objects) == 2
            assert objects[0].object_name == "file1.png"
            assert objects[1].object_name == "file2.png"

    def test_list_objects_with_prefix(self):
        """Test listing objects with prefix filter."""
        with patch("clients.minio_client.Minio") as mock_minio_class:
            mock_client = Mock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = True

            client = MinIOClient()
            client._ensure_bucket()

            client.list_objects(prefix="2026/")

            # Verify list_objects called with prefix
            mock_client.list_objects.assert_called_once()
            call_kwargs = mock_client.list_objects.call_args.kwargs
            assert call_kwargs.get("prefix") == "2026/"

    def test_delete_object_success(self):
        """Test deleting an object."""
        with patch("clients.minio_client.Minio") as mock_minio_class:
            mock_client = Mock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = True

            client = MinIOClient()
            client._ensure_bucket()

            client.delete_object("test.png")

            mock_client.remove_object.assert_called_once_with(client.bucket, "test.png")

    def test_get_object_url(self):
        """Test generating object URL."""
        with patch("clients.minio_client.Minio"):
            client = MinIOClient()

            url = client.get_object_url("test.png")

            # Should generate HTTP URL
            assert "192.168.1.215:9000" in url
            assert "comfy-gen" in url
            assert "test.png" in url

    @patch("clients.minio_client.Minio")
    def test_upload_bytes_success(self, mock_minio_class):
        """Test uploading bytes data."""
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        mock_client.bucket_exists.return_value = True

        client = MinIOClient()
        client._ensure_bucket()

        data = b"test image data"
        client.upload_bytes(data, "test.png")

        # Should call put_object with BytesIO
        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args
        assert call_args[0][0] == client.bucket
        assert call_args[0][1] == "test.png"
        assert isinstance(call_args[0][2], io.BytesIO)
        assert call_args[0][3] == len(data)
