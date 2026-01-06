#!/usr/bin/env python3
"""
MinIO Uploader - Watches directory and uploads images to MinIO bucket.
Run alongside massive_experiment_framework.py to upload images as they're generated.

Usage:
    python scripts/minio_uploader.py --watch /tmp/massive_experiment --once  # Upload existing only
    python scripts/minio_uploader.py --watch /tmp/massive_experiment         # Continuous watch mode
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

# MinIO configuration
MINIO_ENDPOINT = "http://192.168.1.215:9000"
MINIO_BUCKET = "comfy-gen"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of file for deduplication."""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:12]


def upload_to_minio(filepath: Path, remote_name: Optional[str] = None) -> Optional[str]:
    """Upload file to MinIO and return URL."""
    if remote_name is None:
        remote_name = filepath.name

    try:
        # Use curl with S3-style PUT
        url = f"{MINIO_ENDPOINT}/{MINIO_BUCKET}/{remote_name}"

        # Get current date in required format
        datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Use mc (MinIO client) if available, otherwise fall back to curl
        mc_path = Path.home() / ".local" / "bin" / "mc"
        if mc_path.exists():
            result = subprocess.run(
                [str(mc_path), "cp", str(filepath), f"minio/{MINIO_BUCKET}/{remote_name}"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return url

        # Try with curl and anonymous upload (if bucket policy allows)
        result = subprocess.run(
            [
                "curl", "-s", "-w", "%{http_code}",
                "-X", "PUT",
                "-T", str(filepath),
                url,
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip().endswith("200") or result.stdout.strip().endswith("201"):
            return url

        # If curl fails, try using Python's requests
        try:
            import requests
            with open(filepath, "rb") as f:
                response = requests.put(url, data=f)
                if response.status_code in [200, 201]:
                    return url
        except ImportError:
            pass

        # Last resort - use boto3 if available
        try:
            import boto3
            from botocore.client import Config

            s3_client = boto3.client(
                "s3",
                endpoint_url=MINIO_ENDPOINT,
                aws_access_key_id=MINIO_ACCESS_KEY,
                aws_secret_access_key=MINIO_SECRET_KEY,
                config=Config(signature_version="s3v4"),
            )

            s3_client.upload_file(str(filepath), MINIO_BUCKET, remote_name)
            return url

        except ImportError:
            print("  [WARN] boto3 not available")
            return None

    except Exception as e:
        print(f"  [ERROR] Upload failed: {e}")
        return None


def upload_with_metadata(image_path: Path, metadata_dir: Path) -> dict:
    """Upload image and associated metadata."""
    result = {"image": None, "metadata": None, "image_path": str(image_path)}

    # Upload image
    image_url = upload_to_minio(image_path)
    if image_url:
        result["image"] = image_url
        print(f"  [OK] Image: {image_url}")
    else:
        print(f"  [FAIL] Image upload failed: {image_path.name}")
        return result

    # Find and upload associated metadata
    metadata_name = image_path.stem + ".json"
    metadata_path = metadata_dir / metadata_name

    if metadata_path.exists():
        metadata_url = upload_to_minio(metadata_path, f"metadata/{metadata_name}")
        if metadata_url:
            result["metadata"] = metadata_url
            print(f"  [OK] Metadata: {metadata_url}")

    return result


def watch_directory(
    watch_dir: Path,
    metadata_dir: Optional[Path] = None,
    once: bool = False,
    interval: float = 30.0,
) -> None:
    """Watch directory for new images and upload them."""

    if metadata_dir is None:
        metadata_dir = watch_dir / "metadata"

    uploaded: Set[str] = set()
    upload_log = watch_dir / "minio_uploads.json"

    # Load previously uploaded files
    if upload_log.exists():
        try:
            with open(upload_log) as f:
                data = json.load(f)
                uploaded = set(data.get("uploaded_files", []))
                print(f"[INFO] Loaded {len(uploaded)} previously uploaded files")
        except:
            pass

    print(f"[INFO] Watching: {watch_dir}")
    print(f"[INFO] Metadata dir: {metadata_dir}")
    print(f"[INFO] MinIO endpoint: {MINIO_ENDPOINT}/{MINIO_BUCKET}")
    print(f"[INFO] Mode: {'one-time' if once else 'continuous'}")
    print("-" * 60)

    total_uploaded = 0
    total_failed = 0

    while True:
        # Find new images
        image_files = list(watch_dir.glob("*.png")) + list(watch_dir.glob("*.jpg"))
        new_files = [f for f in image_files if f.name not in uploaded]

        if new_files:
            print(f"\n[INFO] Found {len(new_files)} new images to upload")

            for image_path in sorted(new_files):
                print(f"\n  Uploading: {image_path.name}")
                result = upload_with_metadata(image_path, metadata_dir)

                if result["image"]:
                    uploaded.add(image_path.name)
                    total_uploaded += 1

                    # Save progress
                    with open(upload_log, "w") as f:
                        json.dump({
                            "uploaded_files": list(uploaded),
                            "last_upload": datetime.now().isoformat(),
                            "total_uploaded": total_uploaded,
                        }, f, indent=2)
                else:
                    total_failed += 1

        if once:
            break

        # Status update
        current_count = len(list(watch_dir.glob("*.png")))
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Images: {current_count} | Uploaded: {total_uploaded} | Failed: {total_failed}", end="", flush=True)

        time.sleep(interval)

    print(f"\n\n{'='*60}")
    print(f"[COMPLETE] Total uploaded: {total_uploaded}")
    print(f"[COMPLETE] Total failed: {total_failed}")
    print("[COMPLETE] Gallery URL: http://192.168.1.162:8080")


def main():
    parser = argparse.ArgumentParser(description="Upload images to MinIO")
    parser.add_argument("--watch", "-w", type=Path, required=True, help="Directory to watch")
    parser.add_argument("--metadata", "-m", type=Path, help="Metadata directory")
    parser.add_argument("--once", action="store_true", help="Upload existing files and exit")
    parser.add_argument("--interval", type=float, default=30.0, help="Check interval in seconds")

    args = parser.parse_args()

    if not args.watch.exists():
        print(f"[ERROR] Watch directory does not exist: {args.watch}")
        sys.exit(1)

    watch_directory(
        args.watch,
        args.metadata,
        once=args.once,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()
