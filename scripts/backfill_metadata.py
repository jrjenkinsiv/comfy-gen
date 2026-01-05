#!/usr/bin/env python3
"""Backfill missing metadata for images in MinIO.

Creates basic metadata JSON files for images that don't have them.
Uses filename parsing to extract what info we can (timestamp, name).

Run: python3 scripts/backfill_metadata.py [--dry-run]
"""

import json
import os
import sys
from datetime import datetime
from minio import Minio


def parse_filename(filename: str) -> dict:
    """Extract metadata from filename pattern: YYYYMMDD_HHMMSS_description.png"""
    result = {
        "prompt": "No prompt recorded",
        "negative_prompt": "",
        "seed": None,
        "steps": None,
        "cfg": None,
        "loras": []
    }
    
    # Remove .png extension
    base = filename.replace('.png', '')
    parts = base.split('_')
    
    if len(parts) >= 3:
        # Try to parse timestamp
        try:
            date_str = parts[0]
            time_str = parts[1]
            if len(date_str) == 8 and len(time_str) == 6:
                # Valid timestamp format
                result["timestamp"] = f"{date_str}_{time_str}"
                # Rest is description
                description = '_'.join(parts[2:])
                result["prompt"] = f"[Backfilled] {description.replace('_', ' ')}"
        except (ValueError, IndexError):
            pass
    
    return result


def create_metadata(filename: str, file_size: int = None) -> dict:
    """Create metadata structure for an image."""
    parsed = parse_filename(filename)
    
    # Use new nested format
    return {
        "input": {
            "prompt": parsed.get("prompt", "No prompt recorded"),
            "negative_prompt": parsed.get("negative_prompt", "")
        },
        "parameters": {
            "seed": parsed.get("seed"),
            "steps": parsed.get("steps"),
            "cfg": parsed.get("cfg"),
            "loras": parsed.get("loras", []),
            "resolution": None
        },
        "workflow": {
            "name": "unknown",
            "model": "unknown"
        },
        "quality": {
            "grade": None,
            "composite_score": None,
            "prompt_adherence": {
                "clip": None
            },
            "technical": {
                "brisque": None,
                "niqe": None
            }
        },
        "storage": {
            "file_size_bytes": file_size,
            "generation_time_seconds": None,
            "backfilled": True,
            "backfill_date": datetime.now().isoformat()
        }
    }


def main():
    dry_run = "--dry-run" in sys.argv
    
    # Connect to MinIO
    mc = Minio(
        '192.168.1.215:9000',
        access_key=os.environ.get('MINIO_ACCESS_KEY', 'minioadmin'),
        secret_key=os.environ.get('MINIO_SECRET_KEY', 'minioadmin'),
        secure=False
    )
    
    bucket = "comfy-gen"
    
    # List all objects
    print("Fetching object list...")
    objects = list(mc.list_objects(bucket))
    
    # Find images and their metadata
    png_files = {obj.object_name: obj for obj in objects if obj.object_name.endswith('.png')}
    json_keys = {obj.object_name for obj in objects if obj.object_name.endswith('.json')}
    
    # Find missing metadata
    missing = []
    for png_name, png_obj in png_files.items():
        json_key = png_name + '.json'
        if json_key not in json_keys:
            missing.append((png_name, png_obj))
    
    print(f"Found {len(png_files)} images, {len(missing)} missing metadata")
    
    if not missing:
        print("[OK] All images have metadata")
        return 0
    
    if dry_run:
        print("\n[DRY RUN] Would create metadata for:")
        for png_name, _ in sorted(missing)[:20]:
            print(f"  {png_name}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
        return 0
    
    # Create metadata for missing files
    print(f"\nCreating metadata for {len(missing)} images...")
    created = 0
    errors = 0
    
    for png_name, png_obj in missing:
        json_key = png_name + '.json'
        
        try:
            # Create metadata
            metadata = create_metadata(png_name, png_obj.size)
            json_data = json.dumps(metadata, indent=2).encode('utf-8')
            
            # Upload to MinIO
            from io import BytesIO
            mc.put_object(
                bucket,
                json_key,
                BytesIO(json_data),
                len(json_data),
                content_type='application/json'
            )
            created += 1
            print(f"  [OK] {json_key}")
            
        except Exception as e:
            errors += 1
            print(f"  [ERROR] {json_key}: {e}")
    
    print(f"\nComplete: {created} created, {errors} errors")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
