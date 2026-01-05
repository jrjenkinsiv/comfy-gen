"""Client for interacting with HuggingFace Hub API."""

import os
from typing import Any, Dict, List, Optional
from huggingface_hub import HfApi, hf_hub_download, list_models, model_info


class HuggingFaceClient:
    """Client for HuggingFace Hub model discovery and download."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize HuggingFace Hub client.
        
        Args:
            token: HuggingFace API token (optional, required for gated models)
        """
        self.token = token or os.getenv("HF_TOKEN")
        self.api = HfApi(token=self.token)
    
    def search_models(
        self,
        query: Optional[str] = None,
        library: Optional[str] = None,
        tags: Optional[List[str]] = None,
        pipeline_tag: Optional[str] = None,
        sort: str = "downloads",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for models on HuggingFace Hub.
        
        Args:
            query: Search query (optional)
            library: Filter by library (e.g., "diffusers", "transformers")
            tags: Filter by tags (e.g., ["text-to-image", "sdxl"])
            pipeline_tag: Filter by pipeline tag (e.g., "text-to-image")
            sort: Sort method ("downloads", "likes", "created", "modified")
            limit: Maximum results to return
            
        Returns:
            List of model dictionaries with simplified metadata
        """
        try:
            # Build filter - library should be in tags list for newer API
            filter_tags = tags or []
            if library:
                filter_tags.append(library)
            
            # Build filter kwargs
            filter_kwargs = {}
            if filter_tags:
                filter_kwargs["tags"] = filter_tags
            if pipeline_tag:
                filter_kwargs["pipeline_tag"] = pipeline_tag
            
            # Search models
            models = list_models(
                search=query,
                sort=sort,
                direction=-1,  # Descending
                limit=limit,
                **filter_kwargs
            )
            
            # Simplify response format
            results = []
            for model in models:
                results.append({
                    "id": model.id,
                    "author": model.author if hasattr(model, 'author') else model.id.split('/')[0],
                    "name": model.id.split('/')[-1] if '/' in model.id else model.id,
                    "downloads": getattr(model, 'downloads', 0),
                    "likes": getattr(model, 'likes', 0),
                    "tags": getattr(model, 'tags', []),
                    "pipeline_tag": getattr(model, 'pipeline_tag', None),
                    "library": getattr(model, 'library_name', None),
                    "created_at": str(getattr(model, 'created_at', '')),
                    "last_modified": str(getattr(model, 'last_modified', '')),
                })
            
            return results
        except Exception:
            return []
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a model.
        
        Args:
            model_id: HuggingFace model ID (e.g., "stabilityai/stable-diffusion-xl-base-1.0")
            
        Returns:
            Model information dictionary or None on failure
        """
        try:
            info = model_info(model_id, token=self.token)
            
            # Extract key information
            return {
                "id": info.id,
                "author": info.author if hasattr(info, 'author') else info.id.split('/')[0],
                "name": info.id.split('/')[-1] if '/' in info.id else info.id,
                "downloads": getattr(info, 'downloads', 0),
                "likes": getattr(info, 'likes', 0),
                "tags": getattr(info, 'tags', []),
                "pipeline_tag": getattr(info, 'pipeline_tag', None),
                "library": getattr(info, 'library_name', None),
                "created_at": str(getattr(info, 'created_at', '')),
                "last_modified": str(getattr(info, 'last_modified', '')),
                "card_data": getattr(info, 'card_data', {}),
                "sha": getattr(info, 'sha', None),
                "siblings": [
                    {
                        "filename": s.rfilename,
                        "size": getattr(s, 'size', None),
                    }
                    for s in getattr(info, 'siblings', [])
                ],
                "gated": getattr(info, 'gated', False),
            }
        except Exception:
            return None
    
    def get_model_files(self, model_id: str) -> List[Dict[str, Any]]:
        """List all files in a model repository.
        
        Args:
            model_id: HuggingFace model ID
            
        Returns:
            List of file dictionaries with name, size
        """
        try:
            info = model_info(model_id, token=self.token)
            
            files = []
            for sibling in getattr(info, 'siblings', []):
                files.append({
                    "filename": sibling.rfilename,
                    "size": getattr(sibling, 'size', None),
                })
            
            return files
        except Exception:
            return []
    
    def download_file(
        self,
        model_id: str,
        filename: str,
        local_dir: str,
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """Download a specific file from a model repository.
        
        Args:
            model_id: HuggingFace model ID
            filename: File to download (e.g., "model.safetensors")
            local_dir: Local directory to save file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded file or None on failure
        """
        try:
            # Download file
            downloaded_path = hf_hub_download(
                repo_id=model_id,
                filename=filename,
                local_dir=local_dir,
                token=self.token,
            )
            
            return downloaded_path
        except Exception:
            return None
