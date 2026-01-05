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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .stats { color: #888; }
        .view-controls {
            display: flex;
            gap: 5px;
            align-items: center;
        }
        .view-btn {
            padding: 8px 12px;
            border: 1px solid #333;
            border-radius: 5px;
            background: #2a2a4a;
            color: #eee;
            cursor: pointer;
            font-size: 14px;
        }
        .view-btn.active { background: #00d9ff; color: #000; }
        .view-btn:hover:not(.active) { background: #3a3a5a; }
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
        button.secondary {
            background: #2a2a4a;
            color: #eee;
        }
        button.secondary:hover { background: #3a3a5a; }
        button.danger {
            background: #d9005a;
            color: #fff;
        }
        button.danger:hover { background: #b00048; }
        .action-bar {
            display: none;
            gap: 10px;
            margin-bottom: 20px;
            padding: 15px;
            background: #2a2a4a;
            border-radius: 5px;
            flex-wrap: wrap;
        }
        .action-bar.visible { display: flex; }
        .gallery {
            display: grid;
            gap: 20px;
        }
        .gallery.grid-small { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
        .gallery.grid-medium { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
        .gallery.grid-large { grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); }
        .gallery.list-view {
            grid-template-columns: 1fr;
            gap: 10px;
        }
        .card {
            background: #2a2a4a;
            border-radius: 10px;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            position: relative;
        }
        .card:hover { transform: translateY(-5px); box-shadow: 0 4px 20px rgba(0, 217, 255, 0.3); }
        .card.selected {
            box-shadow: 0 0 0 3px #00d9ff;
        }
        .card.favorited::before {
            content: '\\2605';
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 24px;
            color: #ffd700;
            z-index: 10;
            text-shadow: 0 0 3px rgba(0,0,0,0.8);
        }
        .quality-overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 14px;
            z-index: 10;
        }
        .quality-overlay.grade-a { background: rgba(45, 90, 45, 0.9); }
        .quality-overlay.grade-b { background: rgba(58, 90, 58, 0.9); }
        .quality-overlay.grade-c { background: rgba(90, 90, 58, 0.9); }
        .quality-overlay.grade-d { background: rgba(90, 58, 58, 0.9); }
        .quality-overlay.grade-f { background: rgba(90, 42, 42, 0.9); }
        .gallery.list-view .card {
            display: flex;
            flex-direction: row;
        }
        .gallery.list-view .card img {
            width: 200px;
            height: 150px;
            flex-shrink: 0;
        }
        .card img {
            width: 100%;
            object-fit: cover;
        }
        .gallery.grid-small .card img { height: 150px; }
        .gallery.grid-medium .card img { height: 200px; }
        .gallery.grid-large .card img { height: 300px; }
        .card-body { padding: 15px; flex: 1; }
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
        .gallery.list-view .prompt {
            max-height: none;
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
        .tag.grade-a { background: #2d5a2d; font-weight: bold; }
        .tag.grade-b { background: #3a5a3a; }
        .tag.grade-c { background: #5a5a3a; }
        .tag.grade-d { background: #5a3a3a; }
        .tag.grade-f { background: #5a2a2a; }
        .tag.favorite { background: #ffa500; color: #000; cursor: pointer; }
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
        @media (max-width: 768px) {
            .gallery.grid-small { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
            .gallery.grid-medium { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
            .gallery.grid-large { grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }
            .gallery.list-view .card {
                flex-direction: column;
            }
            .gallery.list-view .card img {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>ComfyGen Gallery</h1>
            <div class="stats" id="stats">Loading...</div>
        </div>
        <div class="view-controls">
            <span style="margin-right: 10px; color: #888;">View:</span>
            <button class="view-btn" onclick="setViewMode('grid', 'small')">Grid S</button>
            <button class="view-btn active" onclick="setViewMode('grid', 'medium')">Grid M</button>
            <button class="view-btn" onclick="setViewMode('grid', 'large')">Grid L</button>
            <button class="view-btn" onclick="setViewMode('list', null)">List</button>
        </div>
    </div>
    
    <div class="controls">
        <input type="text" id="search" placeholder="Search prompts..." style="flex: 1; min-width: 200px;">
        <select id="filter">
            <option value="all">All Images</option>
            <option value="lora">With LoRA</option>
            <option value="validated">Validated (CLIP > 0.9)</option>
            <option value="favorites">Favorites</option>
        </select>
        <select id="qualityFilter">
            <option value="all">All Grades</option>
            <option value="a">Grade A</option>
            <option value="b">Grade B+</option>
            <option value="c">Grade C+</option>
            <option value="d">Grade D+</option>
        </select>
        <select id="sort">
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="quality">Quality Score</option>
            <option value="name">Name A-Z</option>
        </select>
        <button onclick="loadGallery()">Refresh</button>
    </div>
    
    <div class="action-bar" id="actionBar">
        <span id="selectedCount">0 selected</span>
        <button class="secondary" onclick="toggleFavoriteSelected()">Toggle Favorite</button>
        <button class="secondary" onclick="downloadSelected()">Download ZIP</button>
        <button class="danger" onclick="deleteSelected()">Delete</button>
        <button class="secondary" onclick="clearSelection()">Clear Selection</button>
    </div>
    
    <div class="gallery grid-medium" id="gallery">
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
        let selectedImages = new Set();
        let favorites = new Set();
        let viewMode = { type: 'grid', size: 'medium' };
        
        // Load preferences from localStorage
        function loadPreferences() {
            const saved = localStorage.getItem('galleryPreferences');
            if (saved) {
                try {
                    const prefs = JSON.parse(saved);
                    viewMode = prefs.viewMode || viewMode;
                    favorites = new Set(prefs.favorites || []);
                    
                    // Restore filters and sort
                    if (prefs.filter) document.getElementById('filter').value = prefs.filter;
                    if (prefs.qualityFilter) document.getElementById('qualityFilter').value = prefs.qualityFilter;
                    if (prefs.sort) document.getElementById('sort').value = prefs.sort;
                } catch (e) {
                    console.error('Failed to load preferences:', e);
                }
            }
            applyViewMode();
        }
        
        // Save preferences to localStorage
        function savePreferences() {
            const prefs = {
                viewMode: viewMode,
                favorites: Array.from(favorites),
                filter: document.getElementById('filter').value,
                qualityFilter: document.getElementById('qualityFilter').value,
                sort: document.getElementById('sort').value
            };
            localStorage.setItem('galleryPreferences', JSON.stringify(prefs));
        }
        
        // Set view mode and update UI
        function setViewMode(type, size) {
            viewMode = { type, size };
            applyViewMode();
            savePreferences();
        }
        
        function applyViewMode() {
            const gallery = document.getElementById('gallery');
            const buttons = document.querySelectorAll('.view-btn');
            
            // Clear existing classes
            gallery.className = 'gallery';
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // Apply new mode
            if (viewMode.type === 'list') {
                gallery.classList.add('list-view');
                document.querySelector('[onclick*="list"]').classList.add('active');
            } else {
                gallery.classList.add(`grid-${viewMode.size}`);
                document.querySelector(`[onclick*="'${viewMode.size}'"]`).classList.add('active');
            }
        }
        
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
                    let meta = { prompt: 'No metadata', loras: [], validation_score: null, quality_grade: null, quality_score: null };
                    
                    if (keys.includes(jsonKey)) {
                        try {
                            const metaResp = await fetch(`${MINIO}/${BUCKET}/${jsonKey}`);
                            const rawMeta = await metaResp.json();
                            
                            // Handle both old flat format and new nested format
                            if (rawMeta.input) {
                                // New nested format
                                meta = {
                                    prompt: rawMeta.input?.prompt || 'No prompt',
                                    negative_prompt: rawMeta.input?.negative_prompt || '',
                                    seed: rawMeta.parameters?.seed,
                                    steps: rawMeta.parameters?.steps,
                                    cfg: rawMeta.parameters?.cfg,
                                    loras: rawMeta.parameters?.loras || [],
                                    validation_score: rawMeta.quality?.prompt_adherence?.clip,
                                    quality_grade: rawMeta.quality?.grade,
                                    quality_score: rawMeta.quality?.composite_score,
                                    quality_technical: rawMeta.quality?.technical?.brisque,
                                    quality_aesthetic: rawMeta.quality?.aesthetic,
                                    quality_detail: rawMeta.quality?.detail,
                                    generation_time: rawMeta.storage?.generation_time_seconds,
                                    file_size: rawMeta.storage?.file_size_bytes,
                                    model: rawMeta.workflow?.model,
                                    resolution: rawMeta.parameters?.resolution
                                };
                            } else {
                                // Old flat format - maintain backward compatibility
                                meta = {
                                    prompt: rawMeta.prompt || 'No prompt',
                                    negative_prompt: rawMeta.negative_prompt || '',
                                    seed: rawMeta.seed,
                                    steps: rawMeta.steps,
                                    cfg: rawMeta.cfg,
                                    loras: rawMeta.loras || [],
                                    validation_score: rawMeta.validation_score,
                                    quality_grade: null,
                                    quality_score: null
                                };
                            }
                        } catch (e) {
                            console.error(`Failed to load metadata for ${png}:`, e);
                        }
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
            const qualityFilter = document.getElementById('qualityFilter').value;
            const sort = document.getElementById('sort').value;
            
            let filtered = allImages.filter(img => {
                if (search && !img.prompt?.toLowerCase().includes(search)) return false;
                if (filter === 'lora' && (!img.loras || img.loras.length === 0)) return false;
                if (filter === 'validated' && (img.validation_score === null || img.validation_score < 0.9)) return false;
                if (filter === 'favorites' && !favorites.has(img.key)) return false;
                
                // Quality grade filter
                if (qualityFilter !== 'all' && img.quality_grade) {
                    const grade = img.quality_grade.toLowerCase();
                    if (qualityFilter === 'a' && grade !== 'a') return false;
                    if (qualityFilter === 'b' && !['a', 'b'].includes(grade)) return false;
                    if (qualityFilter === 'c' && !['a', 'b', 'c'].includes(grade)) return false;
                    if (qualityFilter === 'd' && !['a', 'b', 'c', 'd'].includes(grade)) return false;
                }
                
                return true;
            });
            
            // Apply sorting
            if (sort === 'oldest') {
                filtered.sort((a, b) => a.key.localeCompare(b.key));
            } else if (sort === 'newest') {
                filtered.sort((a, b) => b.key.localeCompare(a.key));
            } else if (sort === 'quality') {
                filtered.sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
            } else if (sort === 'name') {
                filtered.sort((a, b) => a.key.localeCompare(b.key));
            }
            
            const gallery = document.getElementById('gallery');
            
            if (filtered.length === 0) {
                gallery.innerHTML = '<div class="loading">No images match your filters</div>';
                return;
            }
            
            gallery.innerHTML = filtered.map(img => {
                const isFavorite = favorites.has(img.key);
                const isSelected = selectedImages.has(img.key);
                return `
                <div class="card ${isSelected ? 'selected' : ''} ${isFavorite ? 'favorited' : ''}" 
                     data-key="${img.key}"
                     onclick="handleCardClick(event, '${img.key}')">
                    ${img.quality_grade ? `<div class="quality-overlay grade-${img.quality_grade.toLowerCase()}">${img.quality_grade}</div>` : ''}
                    <img src="${img.url}" onclick="openModal(event, '${img.url}')" loading="lazy">
                    <div class="card-body">
                        <div class="card-title">${img.key}</div>
                        <div class="prompt">${escapeHtml(img.prompt || 'No prompt')}</div>
                        <div class="meta">
                            ${img.quality_score ? `<span class="tag score" title="Composite Score">Score: ${img.quality_score.toFixed(1)}/10</span>` : ''}
                            ${isFavorite ? `<span class="tag favorite" onclick="toggleFavorite(event, '${img.key}')">Favorite</span>` : ''}
                            ${img.seed ? `<span class="tag">seed: ${img.seed}</span>` : ''}
                            ${img.steps ? `<span class="tag">steps: ${img.steps}</span>` : ''}
                            ${img.cfg ? `<span class="tag">cfg: ${img.cfg}</span>` : ''}
                            ${img.loras?.map(l => `<span class="tag lora">${l.name.split('.')[0]}:${l.strength}</span>`).join('') || ''}
                            ${img.validation_score !== null ? `<span class="tag score">CLIP: ${img.validation_score.toFixed(2)}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;}).join('');
            
            updateActionBar();
        }
        
        function handleCardClick(event, key) {
            // Don't select if clicking on image (modal) or favorite tag
            if (event.target.tagName === 'IMG' || event.target.classList.contains('favorite')) {
                return;
            }
            
            if (event.ctrlKey || event.metaKey) {
                // Ctrl/Cmd click: toggle selection
                if (selectedImages.has(key)) {
                    selectedImages.delete(key);
                } else {
                    selectedImages.add(key);
                }
            } else if (event.shiftKey && selectedImages.size > 0) {
                // Shift click: select range
                const cards = Array.from(document.querySelectorAll('.card'));
                const lastSelected = Array.from(selectedImages).pop();
                const lastIndex = cards.findIndex(c => c.dataset.key === lastSelected);
                const currentIndex = cards.findIndex(c => c.dataset.key === key);
                
                const start = Math.min(lastIndex, currentIndex);
                const end = Math.max(lastIndex, currentIndex);
                
                for (let i = start; i <= end; i++) {
                    selectedImages.add(cards[i].dataset.key);
                }
            } else {
                // Regular click: select only this one
                selectedImages.clear();
                selectedImages.add(key);
            }
            
            renderGallery();
        }
        
        function toggleFavorite(event, key) {
            event.stopPropagation();
            if (favorites.has(key)) {
                favorites.delete(key);
            } else {
                favorites.add(key);
            }
            savePreferences();
            renderGallery();
        }
        
        function toggleFavoriteSelected() {
            if (selectedImages.size === 0) {
                alert('No images selected');
                return;
            }
            
            selectedImages.forEach(key => {
                if (favorites.has(key)) {
                    favorites.delete(key);
                } else {
                    favorites.add(key);
                }
            });
            
            savePreferences();
            renderGallery();
        }
        
        function clearSelection() {
            selectedImages.clear();
            renderGallery();
        }
        
        function updateActionBar() {
            const actionBar = document.getElementById('actionBar');
            const selectedCount = document.getElementById('selectedCount');
            
            if (selectedImages.size > 0) {
                actionBar.classList.add('visible');
                selectedCount.textContent = `${selectedImages.size} selected`;
            } else {
                actionBar.classList.remove('visible');
            }
        }
        
        async function downloadSelected() {
            if (selectedImages.size === 0) {
                alert('No images selected');
                return;
            }
            
            alert('Download ZIP feature: This would download ' + selectedImages.size + ' images as a ZIP file.\\n\\nNote: This requires server-side implementation to create ZIP archives.');
        }
        
        async function deleteSelected() {
            if (selectedImages.size === 0) {
                alert('No images selected');
                return;
            }
            
            const confirmed = confirm(`Delete ${selectedImages.size} selected image(s)?\\n\\nWarning: This action cannot be undone.`);
            if (!confirmed) return;
            
            alert('Delete feature: This would delete ' + selectedImages.size + ' images from MinIO.\\n\\nNote: This requires server-side implementation with MinIO delete API.');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function openModal(event, url) {
            event.stopPropagation();
            document.getElementById('modal-img').src = url;
            document.getElementById('modal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
        }
        
        // Event listeners
        document.getElementById('search').addEventListener('input', renderGallery);
        document.getElementById('filter').addEventListener('change', () => {
            renderGallery();
            savePreferences();
        });
        document.getElementById('qualityFilter').addEventListener('change', () => {
            renderGallery();
            savePreferences();
        });
        document.getElementById('sort').addEventListener('change', () => {
            renderGallery();
            savePreferences();
        });
        document.addEventListener('keydown', e => { 
            if (e.key === 'Escape') {
                if (document.getElementById('modal').classList.contains('active')) {
                    closeModal();
                } else {
                    clearSelection();
                }
            }
        });
        
        // Initialize
        loadPreferences();
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


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Handle each request in a separate thread to prevent blocking."""
    allow_reuse_address = True
    daemon_threads = True


def main():
    server = ThreadingTCPServer(("", PORT), GalleryHandler)
    with server:
        print(f"[OK] Gallery server running at http://localhost:{PORT}")
        print("[INFO] Press Ctrl+C to stop")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[OK] Server stopped")


if __name__ == "__main__":
    main()
