#!/usr/bin/env python3
"""Create comfy-gen bucket in MinIO on moira.

Run from magneto to create the bucket remotely.
"""

from minio import Minio
from minio.error import S3Error

MINIO_ENDPOINT = "192.168.1.215:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "comfy-gen"

def main():
    print(f"Connecting to MinIO at {MINIO_ENDPOINT}...")

    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )

        # Check if bucket exists
        if client.bucket_exists(BUCKET_NAME):
            print(f"[OK] Bucket '{BUCKET_NAME}' already exists")
        else:
            client.make_bucket(BUCKET_NAME)
            print(f"[OK] Created bucket '{BUCKET_NAME}'")

        # List existing buckets
        buckets = client.list_buckets()
        print("\nAll buckets on MinIO:")
        for bucket in buckets:
            print(f"  - {bucket.name}")

        return 0

    except S3Error as e:
        print(f"[ERROR] MinIO error: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
