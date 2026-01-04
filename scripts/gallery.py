#!/usr/bin/env python3
"""Generate HTML gallery of images in MinIO comfy-gen bucket.

Usage:
    python scripts/gallery.py                        # Generate gallery.html
    python scripts/gallery.py --output my-gallery.html
    python scripts/gallery.py --pattern "sunset"     # Filter by filename pattern
"""

import argparse
import os
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
            
            # Get file extension
            if '.' not in obj.object_name:
                continue
            ext = obj.object_name.lower().rsplit('.', 1)[-1]
            
            # Separate images and videos
            is_image = ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']
            is_video = ext in ['mp4', 'webm']
            
            if not (is_image or is_video):
                continue
            
            images.append({
                'filename': obj.object_name,
                'size': obj.size,
                'last_modified': obj.last_modified,
                'url': f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{obj.object_name}",
                'type': 'image' if is_image else 'video'
            })
        
        # Sort by date, newest first
        images.sort(key=lambda x: x['last_modified'], reverse=True)
        
    except S3Error as e:
        print(f"[ERROR] MinIO error: {e}")
        sys.exit(1)
    
    return images

def generate_gallery_html(images: List[Dict]) -> str:
    """Generate HTML gallery page.
    
    Args:
        images: List of image metadata dictionaries
        
    Returns:
        HTML string
    """
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html>")
    html.append("<head>")
    html.append("  <meta charset='utf-8'>")
    html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append("  <title>ComfyGen Gallery</title>")
    html.append("  <style>")
    html.append("    * { box-sizing: border-box; }")
    html.append("    body {")
    html.append("      font-family: Arial, sans-serif;")
    html.append("      margin: 0;")
    html.append("      padding: 20px;")
    html.append("      background-color: #f5f5f5;")
    html.append("    }")
    html.append("    .header {")
    html.append("      text-align: center;")
    html.append("      margin-bottom: 30px;")
    html.append("    }")
    html.append("    .header h1 {")
    html.append("      color: #333;")
    html.append("      margin: 0 0 10px 0;")
    html.append("    }")
    html.append("    .header p {")
    html.append("      color: #666;")
    html.append("      margin: 0;")
    html.append("    }")
    html.append("    .gallery {")
    html.append("      display: grid;")
    html.append("      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));")
    html.append("      gap: 20px;")
    html.append("      max-width: 1400px;")
    html.append("      margin: 0 auto;")
    html.append("    }")
    html.append("    .gallery-item {")
    html.append("      background: white;")
    html.append("      border-radius: 8px;")
    html.append("      overflow: hidden;")
    html.append("      box-shadow: 0 2px 8px rgba(0,0,0,0.1);")
    html.append("      transition: transform 0.2s, box-shadow 0.2s;")
    html.append("    }")
    html.append("    .gallery-item:hover {")
    html.append("      transform: translateY(-5px);")
    html.append("      box-shadow: 0 4px 16px rgba(0,0,0,0.2);")
    html.append("    }")
    html.append("    .gallery-item img, .gallery-item video {")
    html.append("      width: 100%;")
    html.append("      height: 250px;")
    html.append("      object-fit: cover;")
    html.append("      display: block;")
    html.append("    }")
    html.append("    .gallery-item-info {")
    html.append("      padding: 15px;")
    html.append("    }")
    html.append("    .gallery-item-filename {")
    html.append("      font-weight: bold;")
    html.append("      color: #333;")
    html.append("      margin-bottom: 8px;")
    html.append("      word-break: break-all;")
    html.append("      font-size: 14px;")
    html.append("    }")
    html.append("    .gallery-item-meta {")
    html.append("      font-size: 12px;")
    html.append("      color: #666;")
    html.append("      margin-bottom: 5px;")
    html.append("    }")
    html.append("    .gallery-item-link {")
    html.append("      display: inline-block;")
    html.append("      margin-top: 10px;")
    html.append("      padding: 8px 16px;")
    html.append("      background-color: #4CAF50;")
    html.append("      color: white;")
    html.append("      text-decoration: none;")
    html.append("      border-radius: 4px;")
    html.append("      font-size: 14px;")
    html.append("      transition: background-color 0.2s;")
    html.append("    }")
    html.append("    .gallery-item-link:hover {")
    html.append("      background-color: #45a049;")
    html.append("    }")
    html.append("    .empty-state {")
    html.append("      text-align: center;")
    html.append("      padding: 60px 20px;")
    html.append("      color: #666;")
    html.append("    }")
    html.append("    .video-badge {")
    html.append("      position: absolute;")
    html.append("      top: 10px;")
    html.append("      right: 10px;")
    html.append("      background: rgba(0,0,0,0.7);")
    html.append("      color: white;")
    html.append("      padding: 4px 8px;")
    html.append("      border-radius: 4px;")
    html.append("      font-size: 12px;")
    html.append("    }")
    html.append("    .media-container {")
    html.append("      position: relative;")
    html.append("    }")
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")
    html.append("  <div class='header'>")
    html.append("    <h1>ComfyGen Gallery</h1>")
    
    if images:
        html.append(f"    <p>{len(images)} item(s) found</p>")
    else:
        html.append("    <p>No images found</p>")
    
    html.append("  </div>")
    
    if not images:
        html.append("  <div class='empty-state'>")
        html.append("    <p>No images or videos found in the comfy-gen bucket.</p>")
        html.append("  </div>")
    else:
        html.append("  <div class='gallery'>")
        
        for img in images:
            # Format size
            size_kb = img['size'] / 1024
            if size_kb > 1024:
                size_str = f"{size_kb/1024:.2f} MB"
            else:
                size_str = f"{size_kb:.2f} KB"
            
            # Format date
            date_str = img['last_modified'].strftime("%Y-%m-%d %H:%M")
            
            html.append("    <div class='gallery-item'>")
            html.append("      <div class='media-container'>")
            
            if img['type'] == 'video':
                html.append(f"        <video src='{img['url']}' controls></video>")
                html.append("        <div class='video-badge'>VIDEO</div>")
            else:
                html.append(f"        <img src='{img['url']}' alt='{img['filename']}' loading='lazy'>")
            
            html.append("      </div>")
            html.append("      <div class='gallery-item-info'>")
            html.append(f"        <div class='gallery-item-filename'>{img['filename']}</div>")
            html.append(f"        <div class='gallery-item-meta'>Size: {size_str}</div>")
            html.append(f"        <div class='gallery-item-meta'>Date: {date_str}</div>")
            html.append(f"        <a href='{img['url']}' target='_blank' class='gallery-item-link'>Open Full Size</a>")
            html.append("      </div>")
            html.append("    </div>")
        
        html.append("  </div>")
    
    html.append("</body>")
    html.append("</html>")
    
    return "\n".join(html)

def main():
    parser = argparse.ArgumentParser(
        description="Generate HTML gallery of MinIO comfy-gen bucket",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--output",
        default="gallery.html",
        help="Output HTML file (default: gallery.html)"
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
    
    # Generate gallery HTML
    html = generate_gallery_html(images)
    
    # Write to file
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(html)
        abs_path = os.path.abspath(args.output)
        print(f"[OK] Generated gallery: {args.output}")
        print(f"[INFO] Open in browser: file://{abs_path}")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to write gallery file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
