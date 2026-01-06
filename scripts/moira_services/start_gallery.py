#!/usr/bin/env python3
"""
ComfyGen Gallery Server for moira.
Serves generated images from MinIO bucket with a web UI.

Usage:
    python start_gallery.py
    python start_gallery.py --port 8080
    python start_gallery.py --background
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import argparse
import subprocess
import sys
from datetime import datetime

# Configuration
DEFAULT_PORT = 8080
MINIO_URL = "http://localhost:9000"  # MinIO is on same machine
BUCKET = "comfy-gen"


class GalleryHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for gallery requests."""
    
    def log_message(self, format, *args):
        """Custom logging format."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")
    
    def do_GET(self):
        """Handle GET requests."""
        path = urllib.parse.urlparse(self.path).path
        
        if path == "/" or path == "/index.html":
            self.serve_gallery()
        elif path == "/api/images":
            self.serve_image_list()
        elif path.startswith("/images/"):
            self.proxy_image(path[8:])  # Remove /images/ prefix
        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        else:
            self.send_error(404)
    
    def serve_gallery(self):
        """Serve the gallery HTML page."""
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>ComfyGen Gallery</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e; color: #eee; padding: 20px;
        }
        h1 { text-align: center; margin-bottom: 20px; color: #00d4ff; }
        .gallery { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px; max-width: 1600px; margin: 0 auto;
        }
        .image-card {
            background: #16213e; border-radius: 12px; overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .image-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 8px 25px rgba(0,212,255,0.2);
        }
        .image-card img { 
            width: 100%; height: 300px; object-fit: cover; cursor: pointer;
        }
        .image-info { padding: 12px; font-size: 12px; color: #888; }
        .image-info .filename { color: #00d4ff; font-weight: 500; }
        .modal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.95); z-index: 1000; justify-content: center; align-items: center;
        }
        .modal.active { display: flex; }
        .modal img { max-width: 95%; max-height: 95%; object-fit: contain; }
        .modal-close {
            position: absolute; top: 20px; right: 30px; font-size: 40px;
            color: #fff; cursor: pointer;
        }
        .stats { text-align: center; margin-bottom: 20px; color: #666; }
        .loading { text-align: center; padding: 50px; color: #666; }
    </style>
</head>
<body>
    <h1>ComfyGen Gallery</h1>
    <div class="stats" id="stats">Loading...</div>
    <div class="gallery" id="gallery">
        <div class="loading">Loading images...</div>
    </div>
    <div class="modal" id="modal">
        <span class="modal-close" onclick="closeModal()">&times;</span>
        <img id="modal-img" src="" alt="">
    </div>
    <script>
        async function loadImages() {
            try {
                const resp = await fetch('/api/images');
                const images = await resp.json();
                const gallery = document.getElementById('gallery');
                const stats = document.getElementById('stats');
                
                stats.textContent = `${images.length} images`;
                
                if (images.length === 0) {
                    gallery.innerHTML = '<div class="loading">No images yet</div>';
                    return;
                }
                
                gallery.innerHTML = images.map(img => `
                    <div class="image-card">
                        <img src="/images/${img.name}" alt="${img.name}" 
                             onclick="openModal('/images/${img.name}')" loading="lazy">
                        <div class="image-info">
                            <div class="filename">${img.name}</div>
                            <div>${img.date || ''}</div>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                document.getElementById('gallery').innerHTML = 
                    '<div class="loading">Error loading images: ' + e.message + '</div>';
            }
        }
        
        function openModal(src) {
            document.getElementById('modal-img').src = src;
            document.getElementById('modal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
        }
        
        document.getElementById('modal').onclick = e => {
            if (e.target.id === 'modal') closeModal();
        };
        document.onkeydown = e => { if (e.key === 'Escape') closeModal(); };
        
        loadImages();
    </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", len(html))
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_image_list(self):
        """Get list of images from MinIO."""
        try:
            # List objects in bucket via MinIO S3 API
            url = f"{MINIO_URL}/{BUCKET}/?list-type=2"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read().decode()
            
            # Parse XML response (simple parsing)
            images = []
            import re
            for match in re.finditer(r'<Key>([^<]+)</Key>', data):
                name = match.group(1)
                if name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # Extract date from filename if present (format: YYYYMMDD_HHMMSS_...)
                    date = ""
                    if len(name) > 15 and name[8] == '_':
                        try:
                            date = f"{name[:4]}-{name[4:6]}-{name[6:8]} {name[9:11]}:{name[11:13]}"
                        except:
                            pass
                    images.append({"name": name, "date": date})
            
            # Sort by name (which includes timestamp) descending
            images.sort(key=lambda x: x["name"], reverse=True)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(images).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def proxy_image(self, filename):
        """Proxy image from MinIO."""
        try:
            url = f"{MINIO_URL}/{BUCKET}/{filename}"
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
                content_type = resp.headers.get('Content-Type', 'image/png')
            
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(data))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(404, str(e))


def start_gallery(port: int = DEFAULT_PORT, background: bool = False):
    """Start gallery server."""
    
    if background:
        # Run detached (Windows)
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            [sys.executable, __file__, "--port", str(port)],
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[OK] Gallery started in background on port {port}")
        return
    
    with socketserver.TCPServer(("0.0.0.0", port), GalleryHandler) as httpd:
        print(f"[OK] Gallery server running on http://0.0.0.0:{port}")
        print(f"     MinIO backend: {MINIO_URL}/{BUCKET}")
        print(f"     URL: http://192.168.1.215:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[OK] Gallery server stopped")


def main():
    parser = argparse.ArgumentParser(description="Start gallery server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to run on")
    parser.add_argument("--background", action="store_true", help="Run in background")
    args = parser.parse_args()
    
    start_gallery(port=args.port, background=args.background)


if __name__ == "__main__":
    main()
