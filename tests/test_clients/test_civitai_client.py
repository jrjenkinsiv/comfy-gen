"""Tests for CivitAI client module."""

from unittest.mock import Mock, patch

import pytest

from clients.civitai_client import CivitAIClient


class TestCivitAIClient:
    """Tests for CivitAIClient class."""

    def test_init_default(self):
        """Test client initialization with default parameters."""
        client = CivitAIClient()
        assert client.api_key is None
        assert client.session is not None

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = CivitAIClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test-key-123"

    @patch.dict('os.environ', {'CIVITAI_API_KEY': 'env-key-456'})
    def test_init_uses_env_key(self):
        """Test that client uses environment variable for API key."""
        client = CivitAIClient()
        assert client.api_key == "env-key-456"

    @patch('clients.civitai_client.requests.Session.get')
    def test_search_models_success(self, mock_get):
        """Test search_models returns results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": 1,
                    "name": "Test Model",
                    "type": "LORA",
                    "nsfw": False,
                    "tags": ["realistic", "portrait"],
                    "creator": {"username": "testuser"},
                    "stats": {"downloadCount": 1000, "rating": 4.5}
                }
            ],
            "metadata": {"totalItems": 1}
        }
        mock_get.return_value = mock_response

        client = CivitAIClient()
        results = client.search_models(query="realistic portrait", limit=10)
        
        assert len(results) == 1
        assert results[0]["name"] == "Test Model"
        assert results[0]["type"] == "LORA"
        
        # Verify request was made with correct params
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["query"] == "realistic portrait"

    @patch('clients.civitai_client.requests.Session.get')
    def test_search_models_with_filters(self, mock_get):
        """Test search_models with type and base model filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [], "metadata": {"totalItems": 0}}
        mock_get.return_value = mock_response

        client = CivitAIClient()
        client.search_models(
            query="test",
            model_type="LORA",
            base_model="SD 1.5",
            sort="Highest Rated",
            nsfw=False
        )
        
        # Verify filters passed correctly
        call_kwargs = mock_get.call_args.kwargs
        params = call_kwargs["params"]
        assert params["types"] == "LORA"
        assert params["baseModels"] == "SD 1.5"
        assert params["sort"] == "Highest Rated"
        assert params["nsfw"] is False

    @patch('clients.civitai_client.requests.Session.get')
    def test_search_models_http_error(self, mock_get):
        """Test search_models handles HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_get.return_value = mock_response

        client = CivitAIClient()
        results = client.search_models(query="test")
        
        # Should return empty list on error
        assert results == []

    @patch('clients.civitai_client.requests.Session.get')
    def test_get_model_by_id_success(self, mock_get):
        """Test get_model_by_id returns model details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345,
            "name": "Test Model",
            "type": "Checkpoint",
            "creator": {"username": "testuser"},
            "modelVersions": [
                {
                    "id": 1,
                    "name": "v1.0",
                    "baseModel": "SD 1.5",
                    "files": [{"name": "model.safetensors"}]
                }
            ]
        }
        mock_get.return_value = mock_response

        client = CivitAIClient()
        model = client.get_model_by_id(12345)
        
        assert model is not None
        assert model["id"] == 12345
        assert model["name"] == "Test Model"
        assert len(model["modelVersions"]) == 1

    @patch('clients.civitai_client.requests.Session.get')
    def test_get_model_by_id_not_found(self, mock_get):
        """Test get_model_by_id returns None for 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_get.return_value = mock_response

        client = CivitAIClient()
        model = client.get_model_by_id(99999)
        
        assert model is None

    @patch('clients.civitai_client.requests.Session.get')
    def test_get_model_version_by_hash_success(self, mock_get):
        """Test get_model_version_by_hash returns version info."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "modelId": 12345,
            "name": "v1.0",
            "baseModel": "SD 1.5",
            "files": [
                {
                    "name": "model.safetensors",
                    "downloadUrl": "https://civitai.com/download/..."
                }
            ],
            "trainedWords": ["trigger1", "trigger2"]
        }
        mock_get.return_value = mock_response

        client = CivitAIClient()
        hash_value = "a" * 64  # SHA256 hash
        version = client.get_model_version_by_hash(hash_value)
        
        assert version is not None
        assert version["name"] == "v1.0"
        assert version["baseModel"] == "SD 1.5"
        assert "trigger1" in version["trainedWords"]

    @patch('clients.civitai_client.requests.Session.get')
    def test_get_model_version_by_hash_invalid(self, mock_get):
        """Test get_model_version_by_hash validates hash format."""
        client = CivitAIClient()
        
        # Invalid hash (too short)
        version = client.get_model_version_by_hash("invalid")
        assert version is None
        
        # Should not make API call for invalid hash
        mock_get.assert_not_called()

    @patch('clients.civitai_client.requests.Session.get')
    def test_get_download_url_success(self, mock_get):
        """Test get_download_url returns download URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "files": [
                {
                    "name": "model.safetensors",
                    "downloadUrl": "https://civitai.com/download/123"
                }
            ]
        }
        mock_get.return_value = mock_response

        client = CivitAIClient()
        url = client.get_download_url(version_id=12345)
        
        assert url == "https://civitai.com/download/123"

    @patch('clients.civitai_client.requests.Session.get')
    def test_get_download_url_with_type_filter(self, mock_get):
        """Test get_download_url filters by file type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "files": [
                {
                    "name": "model.ckpt",
                    "type": "Model",
                    "downloadUrl": "https://civitai.com/download/1"
                },
                {
                    "name": "model.safetensors",
                    "type": "Model",
                    "downloadUrl": "https://civitai.com/download/2"
                }
            ]
        }
        mock_get.return_value = mock_response

        client = CivitAIClient()
        url = client.get_download_url(version_id=12345, file_type="safetensors")
        
        # Should return safetensors file
        assert "download/2" in url

    @patch('clients.civitai_client.requests.Session.get')
    def test_get_download_url_no_files(self, mock_get):
        """Test get_download_url returns None when no files."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": []}
        mock_get.return_value = mock_response

        client = CivitAIClient()
        url = client.get_download_url(version_id=12345)
        
        assert url is None
