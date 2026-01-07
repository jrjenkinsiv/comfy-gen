"""API configuration settings."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API configuration loaded from environment variables."""

    # ComfyUI server
    COMFYUI_HOST: str = "192.168.1.215"
    COMFYUI_PORT: int = 8188

    # MinIO storage
    MINIO_ENDPOINT: str = "192.168.1.215:9000"
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = "comfy-gen"

    # MLflow tracking
    MLFLOW_TRACKING_URI: str = "http://192.168.1.162:5001"
    MLFLOW_EXPERIMENT: str = "comfy-gen-intelligent"

    # API server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    @property
    def comfyui_url(self) -> str:
        """Full ComfyUI server URL."""
        return f"http://{self.COMFYUI_HOST}:{self.COMFYUI_PORT}"

    class Config:
        env_prefix = "COMFYGEN_"
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()
