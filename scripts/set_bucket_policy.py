"""Set MinIO bucket policy to public read.

Run this from magneto to make the comfy-gen bucket publicly accessible.
This allows viewing images directly via URL without authentication.
"""

import json
import sys

try:
    from minio import Minio
except ImportError:
    print("[ERROR] minio package not installed. Run: pip install minio")
    sys.exit(1)


MINIO_ENDPOINT = "192.168.1.215:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "comfy-gen"


def main():
    print(f"[INFO] Connecting to MinIO at {MINIO_ENDPOINT}...")

    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    # Check if bucket exists
    if not client.bucket_exists(BUCKET_NAME):
        print(f"[WARN] Bucket '{BUCKET_NAME}' does not exist. Creating...")
        client.make_bucket(BUCKET_NAME)
        print(f"[OK] Bucket '{BUCKET_NAME}' created.")

    # Set public read policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{BUCKET_NAME}/*"],
            }
        ],
    }

    client.set_bucket_policy(BUCKET_NAME, json.dumps(policy))
    print(f"[OK] Bucket '{BUCKET_NAME}' set to public read.")
    print(f"[INFO] Images viewable at: http://{MINIO_ENDPOINT}/{BUCKET_NAME}/<filename>")

    return 0


if __name__ == "__main__":
    sys.exit(main())
