"""Client for interacting with HuggingFace Hub API."""

import os
from typing import Any, Dict, List, Optional
from huggingface_hub import HfApi, hf_hub_download, model_info
from huggingface_hub.utils import RepositoryNotFoundError, GatedRepoError


class HuggingFaceClient:
    """Client for HuggingFace Hub model discovery and download."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize HuggingFace Hub client.
        
        Args:
            token: HuggingFace API token (required for gated models)
        """
        self.token = token or os.getenv("HF_TOKEN")
        self.api = HfApi(token=self.token)
    
    def search_models(
        self,
        query: str = "",
        library: Optional[str] = None,
        pipeline_tag: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort: str = "downloads",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for models on HuggingFace Hub.
        
        Args:
            query: Search query (searches in model name and description)
            library: Filter by library (e.g., 'diffusers', 'transformers')
            pipeline_tag: Filter by pipeline tag (e.g., 'text-to-image', 'image-to-image')
            tags: Additional tags to filter by (e.g., ['sdxl', 'flux', 'lora'])
            sort: Sort method ('downloads', 'likes', 'trending', 'updated')
            limit: Maximum results to return (default: 10)
            
        Returns:
            List of model dictionaries with simplified metadata
        """
        try:
            # Build search filter
            search_filter = None
            if library:
                search_filter = library
            
            # Map sort to HF API parameter
            sort_mapping = {
                "downloads": "downloads",
                "likes": "likes",
                "trending": "trending",
                "updated": "lastModified"
            }
            direction = -1  # Descending order
            
            models = self.api.list_models(
                search=query if query else None,
                filter=search_filter,
                sort=sort_mapping.get(sort, "downloads"),
                direction=direction,
                limit=limit,
                pipeline_tag=pipeline_tag,
                tags=tags,
            )
            
            # Simplify response format to match CivitAI pattern
            results = []
            for model in models:
                results.append({
                    "id": model.id,
                    "name": model.id.split('/')[-1],  # Extract model name from repo ID
                    "author": model.id.split('/')[0] if '/' in model.id else "unknown",
                    "downloads": model.downloads or 0,
                    "likes": model.likes or 0,
                    "tags": model.tags or [],
                    "pipeline_tag": model.pipeline_tag,
                    "library_name": model.library_name,
                    "created_at": str(model.created_at) if model.created_at else None,
                    "last_modified": str(model.last_modified) if model.last_modified else None,
                    "private": model.private,
                    "gated": getattr(model, 'gated', False),
                })
            
            return results
        except Exception as e:
            print(f"[ERROR] HuggingFace search failed: {str(e)}")
            return []
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a model.
        
        Args:
            model_id: HuggingFace model ID (e.g., 'black-forest-labs/FLUX.1-dev')
            
        Returns:
            Model information dictionary or None on failure
        """
        try:
            info = model_info(model_id, token=self.token)
            
            # Extract model card content if available
            model_card = None
            try:
                card_data = self.api.model_card(model_id)
                if card_data:
                    model_card = str(card_data)[:500]  # Truncate to first 500 chars
            except:
                pass
            
            return {
                "id": info.id,
                "author": info.author,
                "sha": info.sha,
                "created_at": str(info.created_at) if info.created_at else None,
                "last_modified": str(info.last_modified) if info.last_modified else None,
                "private": info.private,
                "gated": getattr(info, 'gated', False),
                "downloads": info.downloads or 0,
                "likes": info.likes or 0,
                "tags": info.tags or [],
                "pipeline_tag": info.pipeline_tag,
                "library_name": info.library_name,
                "model_card": model_card,
                "siblings_count": len(info.siblings) if info.siblings else 0,
            }
        except RepositoryNotFoundError:
            return None
        except GatedRepoError:
            return {"error": "Model is gated - requires authentication and acceptance of terms"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_model_files(self, model_id: str) -> List[Dict[str, Any]]:
        """List files in a model repository.
        
        Args:
            model_id: HuggingFace model ID
            
        Returns:
            List of file dictionaries with name, size, and type
        """
        try:
            info = model_info(model_id, token=self.token, files_metadata=True)
            
            if not info.siblings:
                return []
            
            files = []
            for sibling in info.siblings:
                files.append({
                    "filename": sibling.rfilename,
                    "size": sibling.size if hasattr(sibling, 'size') else None,
                    "blob_id": sibling.blob_id if hasattr(sibling, 'blob_id') else None,
                    "lfs": getattr(sibling, 'lfs', None),
                })
            
            return files
        except Exception as e:
            print(f"[ERROR] Failed to list files: {str(e)}")
            return []
    
    def download_file(
        self,
        model_id: str,
        filename: str,
        local_dir: Optional[str] = None,
        cache_dir: Optional[str] = None,
        force_download: bool = False,
    ) -> Optional[str]:
        """Download a specific file from a model repository.
        
        Args:
            model_id: HuggingFace model ID
            filename: Filename to download (e.g., 'diffusion_pytorch_model.safetensors')
            local_dir: Optional local directory to save file (uses HF cache if not provided)
            cache_dir: Optional cache directory (uses default HF cache if not provided)
            force_download: Force re-download even if cached
            
        Returns:
            Path to downloaded file or None on failure
        """
        try:
            filepath = hf_hub_download(
                repo_id=model_id,
                filename=filename,
                token=self.token,
                local_dir=local_dir,
                cache_dir=cache_dir,
                force_download=force_download,
            )
            return filepath
        except RepositoryNotFoundError:
            print(f"[ERROR] Model not found: {model_id}")
            return None
        except GatedRepoError:
            print(f"[ERROR] Model is gated: {model_id}. Accept terms on HuggingFace website.")
            return None
        except Exception as e:
            print(f"[ERROR] Download failed: {str(e)}")
            return None
