#!/usr/bin/env python3
"""Simple gallery server for browsing ComfyGen images in MinIO.

Run: python3 scripts/gallery_server.py
Then open: http://localhost:8080

Shows thumbnails, metadata, and allows filtering/searching.
"""

import http.server
import json
import socket
import sys
import socketserver
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlparse
import io
import requests
from PIL import Image

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
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            padding: 15px 0;
            flex-wrap: wrap;
        }
        .pagination:empty { display: none; }
        .page-btn {
            padding: 8px 14px;
            border: 1px solid #333;
            border-radius: 5px;
            background: #2a2a4a;
            color: #eee;
            cursor: pointer;
            font-size: 14px;
            min-width: 40px;
            text-align: center;
        }
        .page-btn:hover:not(.active):not(:disabled) { background: #3a3a5a; }
        .page-btn.active { background: #00d9ff; color: #000; font-weight: bold; }
        .page-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .page-info { color: #888; font-size: 14px; margin: 0 10px; }
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
        <select id="perPage">
            <option value="10">10 per page</option>
            <option value="20" selected>20 per page</option>
            <option value="50">50 per page</option>
            <option value="100">100 per page</option>
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
    
    <div class="pagination" id="paginationTop"></div>
    
    <div class="gallery grid-medium" id="gallery">
        <div class="loading">Loading gallery...</div>
    </div>
    
    <div class="pagination" id="paginationBottom"></div>
    
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
        let currentPage = 1;
        let perPage = 20;
        
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
                    if (prefs.perPage) {
                        perPage = prefs.perPage;
                        document.getElementById('perPage').value = prefs.perPage;
                    }
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
                sort: document.getElementById('sort').value,
                perPage: perPage
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
            gallery.innerHTML = '<div class="loading">Loading images...</div>';
            
            try {
                // Fetch ALL bucket objects using S3 continuation token pagination
                let keys = [];
                let continuationToken = null;
                let pageCount = 0;
                
                do {
                    let url = `${MINIO}/${BUCKET}/?list-type=2&max-keys=1000`;
                    if (continuationToken) {
                        url += `&continuation-token=${encodeURIComponent(continuationToken)}`;
                    }
                    
                    const resp = await fetch(url);
                    const xml = await resp.text();
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(xml, 'text/xml');
                    
                    // Get keys from this page
                    const pageKeys = Array.from(doc.querySelectorAll('Key')).map(k => k.textContent);
                    keys = keys.concat(pageKeys);
                    
                    // Check for more pages
                    const isTruncated = doc.querySelector('IsTruncated')?.textContent === 'true';
                    continuationToken = isTruncated ? doc.querySelector('NextContinuationToken')?.textContent : null;
                    pageCount++;
                    
                    gallery.innerHTML = `<div class="loading">Loading images... (${keys.length} objects found)</div>`;
                } while (continuationToken);
                
                const pngFiles = keys.filter(k => k.endsWith('.png') && !k.endsWith('.png.json'));
                const jsonKeys = new Set(keys.filter(k => k.endsWith('.json')));
                
                document.getElementById('stats').textContent = `${pngFiles.length} images in gallery`;
                
                // PERFORMANCE FIX: Only load metadata for first page, then lazy-load rest
                // This prevents loading 558+ JSON files upfront
                allImages = pngFiles.map(png => ({
                    key: png,
                    url: `${MINIO}/${BUCKET}/${png}`,
                    prompt: null, // Lazy-loaded
                    metadataLoaded: false
                }));
                
                // Sort newest first by default (by filename which is timestamp-based)
                allImages.sort((a, b) => b.key.localeCompare(a.key));
                
                renderGallery();
            } catch (e) {
                gallery.innerHTML = `<div class="loading">Error loading gallery: ${e.message}</div>`;
            }
        }
        
        // Lazy-load metadata for a specific image
        async function loadMetadata(img) {
            if (img.metadataLoaded) return img;
            
            const jsonKey = img.key + '.json';
            let meta = { prompt: 'No metadata', loras: [], validation_score: null, quality_grade: null, quality_score: null };
            
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
                console.error(`Failed to load metadata for ${img.key}:`, e);
            }
            
            // Update the image object with metadata
            Object.assign(img, meta, { metadataLoaded: true });
            return img;
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
                document.getElementById('paginationTop').innerHTML = '';
                document.getElementById('paginationBottom').innerHTML = '';
                return;
            }
            
            // Pagination
            const totalPages = Math.ceil(filtered.length / perPage);
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;
            
            const startIdx = (currentPage - 1) * perPage;
            const endIdx = Math.min(startIdx + perPage, filtered.length);
            const pageImages = filtered.slice(startIdx, endIdx);
            
            // Lazy-load metadata for current page only
            Promise.all(pageImages.map(img => loadMetadata(img))).then(() => {
                // Re-render after metadata loads to show prompts/loras
                renderCurrentPage(pageImages, currentPage, totalPages, filtered.length, startIdx, endIdx);
            });
            
            // Render immediately with placeholders, metadata will update when loaded
            renderCurrentPage(pageImages, currentPage, totalPages, filtered.length, startIdx, endIdx);
        }
        
        function renderCurrentPage(pageImages, currentPage, totalPages, filteredLength, startIdx, endIdx) {
            const gallery = document.getElementById('gallery');
            
            // Render pagination controls
            const paginationHtml = renderPagination(currentPage, totalPages, filteredLength, startIdx, endIdx);
            document.getElementById('paginationTop').innerHTML = paginationHtml;
            document.getElementById('paginationBottom').innerHTML = paginationHtml;
            
            gallery.innerHTML = pageImages.map(img => {
                const isFavorite = favorites.has(img.key);
                const isSelected = selectedImages.has(img.key);
                const qualityScore = typeof img.quality_score === 'number' ? img.quality_score.toFixed(1) : null;
                const clipScore = typeof img.validation_score === 'number' ? img.validation_score.toFixed(2) : null;
                return `
                <div class="card ${isSelected ? 'selected' : ''} ${isFavorite ? 'favorited' : ''}" 
                     data-key="${img.key}"
                     onclick="handleCardClick(event, '${img.key}')">
                    ${img.quality_grade ? `<div class="quality-overlay grade-${img.quality_grade.toLowerCase()}">${img.quality_grade}</div>` : ''}
                    <img src="/thumbnail?url=${encodeURIComponent(img.url)}" onclick="openModal(event, '${img.url}')" loading="lazy">
                    <div class="card-body">
                        <div class="card-title">${img.key}</div>
                        <div class="prompt">${escapeHtml(img.prompt || 'No prompt')}</div>
                        <div class="meta">
                            ${qualityScore ? `<span class="tag score" title="Composite Score">Score: ${qualityScore}/10</span>` : ''}
                            ${isFavorite ? `<span class="tag favorite" onclick="toggleFavorite(event, '${img.key}')">Favorite</span>` : ''}
                            ${img.seed ? `<span class="tag">seed: ${img.seed}</span>` : ''}
                            ${img.steps ? `<span class="tag">steps: ${img.steps}</span>` : ''}
                            ${img.cfg ? `<span class="tag">cfg: ${img.cfg}</span>` : ''}
                            ${img.loras?.map(l => `<span class="tag lora">${l.name.split('.')[0]}:${l.strength}</span>`).join('') || ''}
                            ${clipScore ? `<span class="tag score">CLIP: ${clipScore}</span>` : ''}
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
        
        function renderPagination(current, total, totalItems, startIdx, endIdx) {
            if (total <= 1) return '';
            
            let html = `<span class="page-info">Showing ${startIdx + 1}-${endIdx} of ${totalItems}</span>`;
            
            // Previous button
            html += `<button class="page-btn" onclick="goToPage(${current - 1})" ${current === 1 ? 'disabled' : ''}>&laquo; Prev</button>`;
            
            // Page numbers with ellipsis
            const pages = [];
            const maxVisible = 7;
            
            if (total <= maxVisible) {
                for (let i = 1; i <= total; i++) pages.push(i);
            } else {
                pages.push(1);
                if (current > 3) pages.push('...');
                
                let start = Math.max(2, current - 1);
                let end = Math.min(total - 1, current + 1);
                
                if (current <= 3) end = 4;
                if (current >= total - 2) start = total - 3;
                
                for (let i = start; i <= end; i++) pages.push(i);
                
                if (current < total - 2) pages.push('...');
                pages.push(total);
            }
            
            for (const p of pages) {
                if (p === '...') {
                    html += `<span class="page-info">...</span>`;
                } else {
                    html += `<button class="page-btn ${p === current ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
                }
            }
            
            // Next button
            html += `<button class="page-btn" onclick="goToPage(${current + 1})" ${current === total ? 'disabled' : ''}>Next &raquo;</button>`;
            
            return html;
        }
        
        function goToPage(page) {
            currentPage = page;
            renderGallery();
            window.scrollTo({ top: 0, behavior: 'smooth' });
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
        document.getElementById('search').addEventListener('input', () => {
            currentPage = 1;  // Reset to first page on search
            renderGallery();
        });
        document.getElementById('filter').addEventListener('change', () => {
            currentPage = 1;  // Reset to first page on filter change
            renderGallery();
            savePreferences();
        });
        document.getElementById('qualityFilter').addEventListener('change', () => {
            currentPage = 1;  // Reset to first page on filter change
            renderGallery();
            savePreferences();
        });
        document.getElementById('sort').addEventListener('change', () => {
            renderGallery();
            savePreferences();
        });
        document.getElementById('perPage').addEventListener('change', (e) => {
            perPage = parseInt(e.target.value);
            currentPage = 1;  // Reset to first page
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
    # Disable HTTP keepalive - close connection after each request
    # This prevents browsers from holding connections open and blocking threads
    protocol_version = "HTTP/1.0"
    
    def log_message(self, format, *args):
        """Enable logging for debugging."""
        import sys
        sys.stderr.write(f"[{self.client_address[0]}:{self.client_address[1]}] {format % args}\n")
        sys.stderr.flush()
    
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
        elif self.path.startswith('/thumbnail'):
            try:
                query = urlparse(self.path).query
                params = parse_qs(query)
                img_url = params.get('url', [None])[0]
                
                if not img_url:
                    self.send_error(400, "Missing 'url' parameter")
                    return

                # Fetch image from MinIO
                resp = requests.get(img_url, timeout=5)
                if resp.status_code != 200:
                    self.send_error(404, "Could not fetch image")
                    return

                # Process image
                img = Image.open(io.BytesIO(resp.content))
                img.thumbnail((350, 350))  # Resize to max 350px (card width covers approx 300px)
                
                # Convert to RGB if necessary (e.g. if RGBA)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                out_io = io.BytesIO()
                img.save(out_io, 'JPEG', quality=85)
                out_io.seek(0)
                
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.send_header('Cache-Control', 'public, max-age=86400')  # Cache for 1 day
                self.end_headers()
                self.wfile.write(out_io.getvalue())
                
            except Exception as e:
                print(f"[ERROR] Thumbnail generation failed: {e}")
                self.send_error(500, f"Internal Server Error: {e}")
        else:
            self.send_error(404)


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Handle each request in a separate thread to prevent blocking."""
    allow_reuse_address = True
    daemon_threads = True
    # Timeout for socket operations - prevents hung client connections from blocking threads forever
    timeout = 30  # Server-level timeout (for accept())
    # Increase listen backlog to handle burst of incoming connections
    request_queue_size = 128

    def finish_request(self, request, client_address):
        """Override to set socket timeout on each request."""
        # Set per-socket timeout to prevent threads blocking on hung clients
        request.settimeout(30)  # 30 second timeout for individual socket operations
        super().finish_request(request, client_address)


def main():
    # Production guardrail: Prevent accidental execution on dev machine (Magneto)
    hostname = socket.gethostname()
    if hostname == "Magneto" and "--dev" not in sys.argv:
        print("\n[ERROR] DEPLOYMENT GUARDRAIL TRIGGERED")
        print("----------------------------------------")
        print(f"You are attempting to run the Gallery Server on {hostname} (Local Host).")
        print("This service is designed to run on Cerebro (192.168.1.162).")
        print("\nTo bypass this and run locally for development, use:")
        print("    python3 scripts/gallery_server.py --dev")
        print("\nExiting to prevent accidental local deployment.")
        sys.exit(1)

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
