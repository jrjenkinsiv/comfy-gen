#!/usr/bin/env python3
"""Simple gallery server for browsing ComfyGen images in MinIO.

Run: python3 scripts/gallery_server.py
Then open: http://localhost:8080

Shows thumbnails, metadata, and allows filtering/searching.
"""

import http.server
import json
import socketserver
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlparse

MINIO_ENDPOINT = "http://192.168.1.215:9000"
BUCKET = "comfy-gen"
PORT = 8080

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>ComfyGen Gallery</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; 
            color: #eee;
            margin: 0;
            padding: 20px;
        }
        h1 { color: #00d9ff; margin-bottom: 10px; }
        .stats { color: #888; margin-bottom: 20px; }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        input, select, button {
            padding: 10px 15px;
            border: 1px solid #333;
            border-radius: 5px;
            background: #2a2a4a;
            color: #eee;
            font-size: 14px;
        }
        input:focus, select:focus { border-color: #00d9ff; outline: none; }
        button { 
            background: #00d9ff; 
            color: #000; 
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #00b8d9; }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #2a2a4a;
            border-radius: 10px;
            overflow: hidden;
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-5px); }
        .card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            cursor: pointer;
        }
        .card-body { padding: 15px; }
        .card-title {
            font-size: 12px;
            color: #888;
            word-break: break-all;
            margin-bottom: 10px;
        }
        .prompt {
            font-size: 13px;
            color: #ccc;
            max-height: 60px;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 10px;
        }
        .meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 11px;
        }
        .tag {
            background: #3a3a5a;
            padding: 3px 8px;
            border-radius: 3px;
        }
        .tag.lora { background: #5a3a7a; }
        .tag.score { background: #3a5a3a; }
        .tag.quality { font-weight: bold; padding: 4px 10px; }
        .tag.quality-a { background: #2d7a2d; color: #fff; }
        .tag.quality-b { background: #4a7a2d; color: #fff; }
        .tag.quality-c { background: #7a7a2d; color: #fff; }
        .tag.quality-d { background: #7a4a2d; color: #fff; }
        .tag.quality-f { background: #7a2d2d; color: #fff; }
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal.active { display: flex; }
        .modal img {
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
        }
        .modal-close {
            position: fixed;
            top: 20px;
            right: 30px;
            font-size: 40px;
            color: #fff;
            cursor: pointer;
        }
        .loading { text-align: center; padding: 50px; color: #888; }
    </style>
</head>
<body>
    <h1>ComfyGen Gallery</h1>
    <div class="stats" id="stats">Loading...</div>
    
    <div class="controls">
        <input type="text" id="search" placeholder="Search prompts..." style="flex: 1; min-width: 200px;">
        <select id="filter">
            <option value="all">All Images</option>
            <option value="lora">With LoRA</option>
            <option value="validated">Validated (score > 0.9)</option>
            <option value="quality-a">Quality: A (8.0+)</option>
            <option value="quality-b">Quality: B (6.5-7.9)</option>
            <option value="quality-c">Quality: C+ (5.0+)</option>
        </select>
        <select id="sort">
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="quality">Highest Quality</option>
        </select>
        <button onclick="loadGallery()">Refresh</button>
    </div>
    
    <div class="gallery" id="gallery">
        <div class="loading">Loading gallery...</div>
    </div>
    
    <div class="modal" id="modal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modal-img" src="">
    </div>
    
    <script>
        const MINIO = '__MINIO_ENDPOINT__';
        const BUCKET = '__BUCKET__';
        let allImages = [];
        
        async function loadGallery() {
            const gallery = document.getElementById('gallery');
            gallery.innerHTML = '<div class="loading">Loading...</div>';
            
            try {
                // Fetch bucket listing
                const resp = await fetch(`${MINIO}/${BUCKET}/?list-type=2&max-keys=500`);
                const xml = await resp.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(xml, 'text/xml');
                
                // Get all keys
                const keys = Array.from(doc.querySelectorAll('Key')).map(k => k.textContent);
                const pngFiles = keys.filter(k => k.endsWith('.png') && !k.endsWith('.png.json'));
                
                document.getElementById('stats').textContent = `${pngFiles.length} images in gallery`;
                
                // Load metadata for each image
                allImages = [];
                for (const png of pngFiles) {
                    const jsonKey = png + '.json';
                    let meta = { prompt: 'No metadata', loras: [], validation_score: null, quality: null };
                    
                    if (keys.includes(jsonKey)) {
                        try {
                            const metaResp = await fetch(`${MINIO}/${BUCKET}/${jsonKey}`);
                            meta = await metaResp.json();
                        } catch (e) {}
                    }
                    
                    allImages.push({
                        key: png,
                        url: `${MINIO}/${BUCKET}/${png}`,
                        ...meta
                    });
                }
                
                // Sort newest first by default
                allImages.sort((a, b) => b.key.localeCompare(a.key));
                
                renderGallery();
            } catch (e) {
                gallery.innerHTML = `<div class="loading">Error loading gallery: ${e.message}</div>`;
            }
        }
        
        function renderGallery() {
            const search = document.getElementById('search').value.toLowerCase();
            const filter = document.getElementById('filter').value;
            const sort = document.getElementById('sort').value;
            
            let filtered = allImages.filter(img => {
                if (search && !img.prompt?.toLowerCase().includes(search)) return false;
                if (filter === 'lora' && (!img.loras || img.loras.length === 0)) return false;
                if (filter === 'validated' && (img.validation_score === null || img.validation_score < 0.9)) return false;
                if (filter === 'quality-a' && (!img.quality || img.quality.composite_score < 8.0)) return false;
                if (filter === 'quality-b' && (!img.quality || img.quality.composite_score < 6.5 || img.quality.composite_score >= 8.0)) return false;
                if (filter === 'quality-c' && (!img.quality || img.quality.composite_score < 5.0)) return false;
                return true;
            });
            
            if (sort === 'oldest') {
                filtered.sort((a, b) => a.key.localeCompare(b.key));
            } else if (sort === 'quality') {
                filtered.sort((a, b) => {
                    const scoreA = a.quality?.composite_score || 0;
                    const scoreB = b.quality?.composite_score || 0;
                    return scoreB - scoreA;
                });
            } else {
                filtered.sort((a, b) => b.key.localeCompare(a.key));
            }
            
            const gallery = document.getElementById('gallery');
            
            if (filtered.length === 0) {
                gallery.innerHTML = '<div class="loading">No images match your filters</div>';
                return;
            }
            
            gallery.innerHTML = filtered.map(img => `
                <div class="card">
                    <img src="${img.url}" onclick="openModal('${img.url}')" loading="lazy">
                    <div class="card-body">
                        <div class="card-title">${img.key}</div>
                        <div class="prompt">${escapeHtml(img.prompt || 'No prompt')}</div>
                        <div class="meta">
                            ${img.seed ? `<span class="tag">seed: ${img.seed}</span>` : ''}
                            ${img.steps ? `<span class="tag">steps: ${img.steps}</span>` : ''}
                            ${img.cfg ? `<span class="tag">cfg: ${img.cfg}</span>` : ''}
                            ${img.loras?.map(l => `<span class="tag lora">${l.name.split('.')[0]}:${l.strength}</span>`).join('') || ''}
                            ${img.validation_score !== null ? `<span class="tag score">CLIP: ${img.validation_score.toFixed(2)}</span>` : ''}
                            ${img.quality ? `<span class="tag quality quality-${img.quality.grade.toLowerCase()}">${img.quality.grade}: ${img.quality.composite_score.toFixed(1)}</span>` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function openModal(url) {
            document.getElementById('modal-img').src = url;
            document.getElementById('modal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
        }
        
        document.getElementById('search').addEventListener('input', renderGallery);
        document.getElementById('filter').addEventListener('change', renderGallery);
        document.getElementById('sort').addEventListener('change', renderGallery);
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
        
        loadGallery();
    </script>
</body>
</html>
""".replace('__MINIO_ENDPOINT__', MINIO_ENDPOINT).replace('__BUCKET__', BUCKET)


class GalleryHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            content = HTML_TEMPLATE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        pass  # Suppress logging


def main():
    with socketserver.TCPServer(("", PORT), GalleryHandler) as httpd:
        print(f"[OK] Gallery server running at http://localhost:{PORT}")
        print("[INFO] Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[OK] Server stopped")


if __name__ == "__main__":
    main()
