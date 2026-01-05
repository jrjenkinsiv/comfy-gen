"""Client for interacting with CivitAI API."""

import os
from typing import Any, Dict, List, Optional
import requests


class CivitAIClient:
    """Client for CivitAI model discovery and download."""
    
    BASE_URL = "https://civitai.com/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize CivitAI client.
        
        Args:
            api_key: CivitAI API key (optional, enables NSFW content)
        """
        self.api_key = api_key or os.getenv("CIVITAI_API_KEY")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
    
    def search_models(
        self,
        query: str,
        model_type: Optional[str] = None,
        base_model: Optional[str] = None,
        sort: str = "Most Downloaded",
        nsfw: bool = True,
        limit: int = 10,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """Search for models on CivitAI.
        
        Args:
            query: Search query
            model_type: Filter by type (Checkpoint, LORA, VAE, etc.)
            base_model: Filter by base model (SD 1.5, SDXL, etc.)
            sort: Sort method (Most Downloaded, Highest Rated, Newest)
            nsfw: Include NSFW results
            limit: Maximum results to return
            page: Page number (ignored when using query search)
            
        Returns:
            List of model dictionaries
        """
        params = {
            "query": query,
            "limit": limit,
            # Note: CivitAI API doesn't support 'page' with query search
            # Use cursor-based pagination for future implementation
            "sort": sort,
            "nsfw": str(nsfw).lower()
        }
        
        if model_type:
            params["types"] = model_type
        
        if base_model:
            params["baseModels"] = base_model
        
        try:
            response = self.session.get(f"{self.BASE_URL}/models", params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                # Simplify response format
                results = []
                for item in items:
                    model_versions = item.get("modelVersions", [])
                    latest_version = model_versions[0] if model_versions else {}
                    
                    # Get preview image
                    preview_url = None
                    images = latest_version.get("images", [])
                    if images:
                        preview_url = images[0].get("url")
                    
                    # Get download URL
                    download_url = None
                    files = latest_version.get("files", [])
                    if files:
                        download_url = files[0].get("downloadUrl")
                    
                    results.append({
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "type": item.get("type"),
                        "description": item.get("description", "")[:200],  # Truncate
                        "creator": item.get("creator", {}).get("username"),
                        "downloads": item.get("stats", {}).get("downloadCount", 0),
                        "rating": item.get("stats", {}).get("rating", 0),
                        "base_model": latest_version.get("baseModel"),
                        "version_id": latest_version.get("id"),
                        "version_name": latest_version.get("name"),
                        "preview_url": preview_url,
                        "download_url": download_url,
                        "nsfw": item.get("nsfw", False)
                    })
                
                return results
            return []
        except Exception:
            return []
    
    def get_model(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a model.
        
        Args:
            model_id: CivitAI model ID
            
        Returns:
            Model information dictionary or None on failure
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/models/{model_id}", timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_model_version(self, version_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific model version.
        
        Args:
            version_id: CivitAI model version ID
            
        Returns:
            Version information dictionary or None on failure
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/model-versions/{version_id}", timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_model_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Look up model version by file hash (SHA256, AutoV2, etc).
        
        This is the AUTHORITATIVE way to identify what base model a LoRA
        or checkpoint is designed for. Use this instead of guessing by file size.
        
        Args:
            file_hash: SHA256 hash of the .safetensors file
            
        Returns:
            Model version info including baseModel, trainedWords, modelId
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/model-versions/by-hash/{file_hash}",
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "model_name": data.get("model", {}).get("name"),
                    "model_id": data.get("modelId"),
                    "version_id": data.get("id"),
                    "version_name": data.get("name"),
                    "base_model": data.get("baseModel"),
                    "trained_words": data.get("trainedWords", []),
                    "download_url": data.get("downloadUrl"),
                    "files": data.get("files", []),
                }
            elif response.status_code == 404:
                return {"error": "Not found on CivitAI"}
            return None
        except Exception as e:
            return {"error": str(e)}
    
    def get_download_url(
        self,
        model_id: int,
        version_id: Optional[int] = None
    ) -> Optional[str]:
        """Get download URL for a model.
        
        Args:
            model_id: CivitAI model ID
            version_id: Optional specific version ID (uses latest if not provided)
            
        Returns:
            Download URL or None on failure
        """
        model = self.get_model(model_id)
        if not model:
            return None
        
        versions = model.get("modelVersions", [])
        if not versions:
            return None
        
        # Find specific version or use latest
        if version_id:
            version = next((v for v in versions if v.get("id") == version_id), None)
            if not version:
                return None
        else:
            version = versions[0]  # Latest version
        
        files = version.get("files", [])
        if not files:
            return None
        
        # Prefer primary file
        primary_file = next((f for f in files if f.get("primary", False)), files[0])
        return primary_file.get("downloadUrl")
    
    def download_model(
        self,
        download_url: str,
        output_path: str,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Download a model file.
        
        Args:
            download_url: URL to download from
            output_path: Local path to save file
            progress_callback: Optional callback for progress updates (bytes_downloaded, total_bytes)
            
        Returns:
            True on success, False on failure
        """
        try:
            # Add API key to download URL if available
            if self.api_key and "?" in download_url:
                download_url += f"&token={self.api_key}"
            elif self.api_key:
                download_url += f"?token={self.api_key}"
            
            response = self.session.get(download_url, stream=True, timeout=60)
            if response.status_code != 200:
                return False
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            return True
        except Exception:
            return False
