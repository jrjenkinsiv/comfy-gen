"""Client for interacting with MinIO object storage."""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error


class MinIOClient:
    """Client for MinIO storage operations."""
    
    def __init__(
        self,
        endpoint: str = "192.168.1.215:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket: str = "comfy-gen",
        secure: bool = False
    ):
        """Initialize MinIO client.
        
        Args:
            endpoint: MinIO server endpoint
            access_key: Access key
            secret_key: Secret key
            bucket: Default bucket name
            secure: Whether to use HTTPS
        """
        self.endpoint = endpoint
        self.bucket = bucket
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # Note: Bucket existence check is deferred to first operation
        # to avoid blocking on client creation
        self._bucket_checked = False
    
    def _ensure_bucket(self):
        """Ensure bucket exists (called lazily)."""
        if not self._bucket_checked:
            try:
                if not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
            except S3Error:
                pass  # Bucket may already exist
            finally:
                self._bucket_checked = True
    
    def upload_file(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        bucket: Optional[str] = None
    ) -> Optional[str]:
        """Upload a file to MinIO.
        
        Args:
            file_path: Path to file to upload
            object_name: Object name in bucket (defaults to filename)
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            Public URL of uploaded file or None on failure
        """
        self._ensure_bucket()
        bucket = bucket or self.bucket
        
        if object_name is None:
            object_name = Path(file_path).name
        
        try:
            self.client.fput_object(bucket, object_name, file_path)
            return f"http://{self.endpoint}/{bucket}/{object_name}"
        except S3Error:
            return None
    
    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None
    ) -> Optional[str]:
        """Upload bytes to MinIO.
        
        Args:
            data: Bytes to upload
            object_name: Object name in bucket
            content_type: MIME type
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            Public URL of uploaded data or None on failure
        """
        self._ensure_bucket()
        bucket = bucket or self.bucket
        
        try:
            data_stream = io.BytesIO(data)
            self.client.put_object(
                bucket,
                object_name,
                data_stream,
                length=len(data),
                content_type=content_type
            )
            return f"http://{self.endpoint}/{bucket}/{object_name}"
        except S3Error:
            return None
    
    def download_file(
        self,
        object_name: str,
        file_path: str,
        bucket: Optional[str] = None
    ) -> bool:
        """Download a file from MinIO.
        
        Args:
            object_name: Object name in bucket
            file_path: Local path to save file
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            True on success, False on failure
        """
        bucket = bucket or self.bucket
        
        try:
            self.client.fget_object(bucket, object_name, file_path)
            return True
        except S3Error:
            return False
    
    def list_objects(
        self,
        prefix: str = "",
        bucket: Optional[str] = None,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """List objects in bucket.
        
        Args:
            prefix: Object name prefix filter
            bucket: Bucket name (defaults to self.bucket)
            recursive: Whether to list recursively
            
        Returns:
            List of object dictionaries with metadata
        """
        self._ensure_bucket()
        bucket = bucket or self.bucket
        
        objects = []
        try:
            for obj in self.client.list_objects(bucket, prefix=prefix, recursive=recursive):
                objects.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag,
                    "url": f"http://{self.endpoint}/{bucket}/{obj.object_name}"
                })
        except S3Error:
            pass
        
        return objects
    
    def delete_object(
        self,
        object_name: str,
        bucket: Optional[str] = None
    ) -> bool:
        """Delete an object from MinIO.
        
        Args:
            object_name: Object name in bucket
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            True on success, False on failure
        """
        bucket = bucket or self.bucket
        
        try:
            self.client.remove_object(bucket, object_name)
            return True
        except S3Error:
            return False
    
    def get_object_info(
        self,
        object_name: str,
        bucket: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get information about an object.
        
        Args:
            object_name: Object name in bucket
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            Object metadata dictionary or None if not found
        """
        bucket = bucket or self.bucket
        
        try:
            stat = self.client.stat_object(bucket, object_name)
            return {
                "name": stat.object_name,
                "size": stat.size,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "url": f"http://{self.endpoint}/{bucket}/{stat.object_name}"
            }
        except S3Error:
            return None
    
    def object_exists(
        self,
        object_name: str,
        bucket: Optional[str] = None
    ) -> bool:
        """Check if an object exists.
        
        Args:
            object_name: Object name in bucket
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            True if object exists, False otherwise
        """
        return self.get_object_info(object_name, bucket) is not None
