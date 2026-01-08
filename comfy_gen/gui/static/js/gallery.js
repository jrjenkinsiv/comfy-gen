/**
 * Gallery page logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const galleryGrid = document.getElementById('gallery-grid');
    const favoritesOnly = document.getElementById('favorites-only');
    const minRating = document.getElementById('min-rating');
    const categoryFilter = document.getElementById('category-filter');

    // Guard against missing elements
    if (!galleryGrid) {
        console.error('Gallery grid element not found');
        return;
    }

    let currentFilters = {
        favoritesOnly: false,
        minRating: 4,
        category: ''
    };

    // Load gallery
    async function loadGallery() {
        galleryGrid.innerHTML = '<div class="loading-state">Loading images...</div>';
        
        try {
            // For now, load favorites as the gallery source
            const favorites = await api.listFavorites(50, 0);
            
            if (!favorites || favorites.length === 0) {
                galleryGrid.innerHTML = '<div class="empty-state"><p>No images found. Generate some images first!</p></div>';
                return;
            }
            
            // Apply filters
            let filtered = favorites;
            
            if (currentFilters.favoritesOnly) {
                filtered = filtered.filter(f => f.is_favorite);
            }
            
            if (currentFilters.minRating > 1) {
                filtered = filtered.filter(f => (f.rating || 0) >= currentFilters.minRating);
            }
            
            if (currentFilters.category) {
                const cat = currentFilters.category.toLowerCase();
                filtered = filtered.filter(f => {
                    const cats = f.categories || f.source_categories || [];
                    return cats.some(c => c.toLowerCase().includes(cat));
                });
            }
            
            if (filtered.length === 0) {
                galleryGrid.innerHTML = '<div class="empty-state"><p>No images match your filters.</p></div>';
                return;
            }
            
            renderGallery(filtered);
        } catch (err) {
            galleryGrid.innerHTML = '<div class="empty-state"><p>Failed to load images: ' + err.message + '</p></div>';
        }
    }

    function renderGallery(items) {
        galleryGrid.innerHTML = '';
        
        items.forEach(item => {
            const el = createGalleryItem(item);
            galleryGrid.appendChild(el);
        });
    }

    function createGalleryItem(item) {
        const div = document.createElement('div');
        div.className = 'gallery-item';
        
        const imageUrl = item.image_url || item.thumbnail_url || '/gui/static/placeholder.png';
        const date = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
        
        div.innerHTML = 
            '<img src="' + imageUrl + '" alt="Generated image" loading="lazy" onerror="this.style.display=\'none\'">' +
            '<div class="overlay">' +
                '<span class="date">' + date + '</span>' +
            '</div>';
        
        div.addEventListener('click', () => {
            // Open image in new tab for now
            window.open(imageUrl, '_blank');
        });
        
        return div;
    }

    // Filter event listeners
    if (favoritesOnly) {
        favoritesOnly.addEventListener('change', () => {
            currentFilters.favoritesOnly = favoritesOnly.checked;
            loadGallery();
        });
    }

    if (minRating) {
        minRating.addEventListener('change', () => {
            currentFilters.minRating = parseInt(minRating.value) || 1;
            loadGallery();
        });
    }

    if (categoryFilter) {
        let debounceTimer;
        categoryFilter.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                currentFilters.category = categoryFilter.value.trim();
                loadGallery();
            }, 300);
        });
    }

    // Initial load
    loadGallery();
});
