#!/usr/bin/env python3
"""List images in MinIO comfy-gen bucket.

Usage:
    python scripts/list_images.py                    # List all images (text format)
    python scripts/list_images.py --format json      # JSON output
    python scripts/list_images.py --format html      # HTML output
    python scripts/list_images.py --pattern "sunset" # Filter by filename pattern
"""

import argparse
import json
import sys
from datetime import datetime
from typing import List, Dict

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    print("[ERROR] minio package not installed. Run: pip install minio")
    sys.exit(1)

MINIO_ENDPOINT = "192.168.1.215:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "comfy-gen"

def get_images(client: Minio, pattern: str = None) -> List[Dict]:
    """Get list of images from MinIO bucket.
    
    Args:
        client: MinIO client instance
        pattern: Optional filename pattern to filter by
        
    Returns:
        List of dictionaries containing image metadata
    """
    images = []
    
    try:
        objects = client.list_objects(BUCKET_NAME, recursive=True)
        
        for obj in objects:
            # Filter by pattern if provided
            if pattern and pattern.lower() not in obj.object_name.lower():
                continue
            
            # Filter to image/video files
            if '.' not in obj.object_name:
                continue
            ext = obj.object_name.lower().rsplit('.', 1)[-1]
            if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm']:
                continue
            
            images.append({
                'filename': obj.object_name,
                'size': obj.size,
                'last_modified': obj.last_modified,
                'url': f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{obj.object_name}"
            })
        
        # Sort by date, newest first
        images.sort(key=lambda x: x['last_modified'], reverse=True)
        
    except S3Error as e:
        print(f"[ERROR] MinIO error: {e}")
        sys.exit(1)
    
    return images

def format_text(images: List[Dict]) -> str:
    """Format images as text output."""
    if not images:
        return "No images found."
    
    output = []
    output.append(f"Found {len(images)} image(s):\n")
    
    for img in images:
        # Format size
        size_kb = img['size'] / 1024
        if size_kb > 1024:
            size_str = f"{size_kb/1024:.2f} MB"
        else:
            size_str = f"{size_kb:.2f} KB"
        
        # Format date
        date_str = img['last_modified'].strftime("%Y-%m-%d %H:%M:%S")
        
        output.append(f"  {img['filename']}")
        output.append(f"    Size: {size_str}")
        output.append(f"    Date: {date_str}")
        output.append(f"    URL:  {img['url']}")
        output.append("")
    
    return "\n".join(output)

def format_json(images: List[Dict]) -> str:
    """Format images as JSON output."""
    # Convert datetime to string for JSON serialization
    json_data = []
    for img in images:
        json_data.append({
            'filename': img['filename'],
            'size': img['size'],
            'last_modified': img['last_modified'].isoformat(),
            'url': img['url']
        })
    
    return json.dumps(json_data, indent=2)

def format_html(images: List[Dict]) -> str:
    """Format images as HTML table."""
    if not images:
        return "<html><body><p>No images found.</p></body></html>"
    
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html>")
    html.append("<head>")
    html.append("  <meta charset='utf-8'>")
    html.append("  <title>ComfyGen Images</title>")
    html.append("  <style>")
    html.append("    body { font-family: Arial, sans-serif; margin: 20px; }")
    html.append("    table { border-collapse: collapse; width: 100%; }")
    html.append("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
    html.append("    th { background-color: #4CAF50; color: white; }")
    html.append("    tr:nth-child(even) { background-color: #f2f2f2; }")
    html.append("    a { color: #4CAF50; text-decoration: none; }")
    html.append("    a:hover { text-decoration: underline; }")
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")
    html.append(f"  <h1>ComfyGen Images ({len(images)} found)</h1>")
    html.append("  <table>")
    html.append("    <tr>")
    html.append("      <th>Filename</th>")
    html.append("      <th>Size</th>")
    html.append("      <th>Date</th>")
    html.append("      <th>Link</th>")
    html.append("    </tr>")
    
    for img in images:
        # Format size
        size_kb = img['size'] / 1024
        if size_kb > 1024:
            size_str = f"{size_kb/1024:.2f} MB"
        else:
            size_str = f"{size_kb:.2f} KB"
        
        # Format date
        date_str = img['last_modified'].strftime("%Y-%m-%d %H:%M:%S")
        
        html.append("    <tr>")
        html.append(f"      <td>{img['filename']}</td>")
        html.append(f"      <td>{size_str}</td>")
        html.append(f"      <td>{date_str}</td>")
        html.append(f"      <td><a href='{img['url']}' target='_blank'>View</a></td>")
        html.append("    </tr>")
    
    html.append("  </table>")
    html.append("</body>")
    html.append("</html>")
    
    return "\n".join(html)

def main():
    parser = argparse.ArgumentParser(
        description="List images in MinIO comfy-gen bucket",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--pattern",
        help="Filter by filename pattern (case-insensitive)"
    )
    args = parser.parse_args()
    
    # Connect to MinIO
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        
        # Check if bucket exists
        if not client.bucket_exists(BUCKET_NAME):
            print(f"[ERROR] Bucket '{BUCKET_NAME}' does not exist")
            return 1
        
    except Exception as e:
        print(f"[ERROR] Failed to connect to MinIO: {e}")
        return 1
    
    # Get images
    images = get_images(client, args.pattern)
    
    # Format output
    if args.format == "json":
        output = format_json(images)
    elif args.format == "html":
        output = format_html(images)
    else:
        output = format_text(images)
    
    print(output)
    return 0

if __name__ == "__main__":
    sys.exit(main())
