/**
 * Favorites Gallery page logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const galleryGrid = document.getElementById('gallery-grid');
    const loadMoreBtn = document.getElementById('load-more');
    const sortSelect = document.getElementById('sort-by');
    const favoriteModal = document.getElementById('favorite-modal');
    const modalClose = document.getElementById('modal-close');
    
    // Modal content
    const modalImage = document.getElementById('modal-image');
    const modalPrompt = document.getElementById('modal-prompt');
    const modalSettings = document.getElementById('modal-settings');
    const copyRecipeBtn = document.getElementById('copy-recipe');
    const downloadImageBtn = document.getElementById('download-image');
    const deleteBtn = document.getElementById('delete-favorite');
    const regenBtn = document.getElementById('regen-favorite');
    
    let currentOffset = 0;
    const pageSize = 20;
    let allFavorites = [];
    let currentFavorite = null;

    // Load favorites
    async function loadFavorites(append = false) {
        try {
            if (!append) {
                galleryGrid.innerHTML = '<div class="loading-state">Loading favorites...</div>';
                currentOffset = 0;
            }
            
            const favorites = await api.listFavorites(pageSize, currentOffset);
            
            if (!append) {
                allFavorites = favorites;
                galleryGrid.innerHTML = '';
            } else {
                allFavorites = [...allFavorites, ...favorites];
            }
            
            if (favorites.length === 0 && !append) {
                galleryGrid.innerHTML = '<div class="empty-state">No favorites yet. Generate some images and save your favorites!</div>';
                loadMoreBtn.classList.add('hidden');
                return;
            }
            
            renderFavorites(favorites, append);
            currentOffset += favorites.length;
            
            // Show/hide load more button
            if (favorites.length < pageSize) {
                loadMoreBtn.classList.add('hidden');
            } else {
                loadMoreBtn.classList.remove('hidden');
            }
        } catch (err) {
            galleryGrid.innerHTML = `<div class="empty-state">Failed to load favorites: ${err.message}</div>`;
        }
    }

    function renderFavorites(favorites, append = false) {
        if (!append) {
            galleryGrid.innerHTML = '';
        }
        
        favorites.forEach(favorite => {
            const item = createGalleryItem(favorite);
            galleryGrid.appendChild(item);
        });
    }

    function createGalleryItem(favorite) {
        const item = document.createElement('div');
        item.className = 'gallery-item';
        item.dataset.id = favorite.id;
        
        const imageUrl = favorite.image_url || favorite.thumbnail_url || '/static/placeholder.png';
        const createdAt = favorite.created_at ? new Date(favorite.created_at).toLocaleDateString() : '';
        
        item.innerHTML = `
            <img src="${imageUrl}" alt="Favorite image" loading="lazy" onerror="this.src='/static/placeholder.png'">
            <div class="overlay">
                <span class="date">${createdAt}</span>
            </div>
        `;
        
        item.addEventListener('click', () => openFavoriteModal(favorite));
        
        return item;
    }

    async function openFavoriteModal(favorite) {
        currentFavorite = favorite;
        
        modalImage.src = favorite.image_url || '/static/placeholder.png';
        
        // Extract recipe
        try {
            const recipe = await api.extractRecipe(favorite.id);
            modalPrompt.textContent = recipe.prompt || 'No prompt available';
            
            const settings = [];
            if (recipe.checkpoint) settings.push(`Checkpoint: ${recipe.checkpoint}`);
            if (recipe.width && recipe.height) settings.push(`Size: ${recipe.width}x${recipe.height}`);
            if (recipe.steps) settings.push(`Steps: ${recipe.steps}`);
            if (recipe.cfg) settings.push(`CFG: ${recipe.cfg}`);
            if (recipe.seed) settings.push(`Seed: ${recipe.seed}`);
            if (recipe.loras && recipe.loras.length > 0) {
                const loraNames = recipe.loras.map(l => l.name || l).join(', ');
                settings.push(`LoRAs: ${loraNames}`);
            }
            
            modalSettings.innerHTML = settings.map(s => `<div>${s}</div>`).join('');
            
            downloadImageBtn.href = favorite.image_url;
            downloadImageBtn.download = favorite.filename || 'favorite.png';
        } catch (err) {
            modalPrompt.textContent = 'Failed to load recipe';
            modalSettings.innerHTML = '';
        }
        
        favoriteModal.classList.remove('hidden');
    }

    // Load more button
    loadMoreBtn.addEventListener('click', () => {
        loadFavorites(true);
    });

    // Sort change
    sortSelect.addEventListener('change', () => {
        // TODO: Implement sorting via API or client-side
        const sorted = [...allFavorites];
        if (sortSelect.value === 'oldest') {
            sorted.reverse();
        }
        galleryGrid.innerHTML = '';
        renderFavorites(sorted);
    });

    // Modal close
    modalClose.addEventListener('click', () => {
        favoriteModal.classList.add('hidden');
    });

    favoriteModal.addEventListener('click', (e) => {
        if (e.target === favoriteModal) {
            favoriteModal.classList.add('hidden');
        }
    });

    // Copy recipe
    copyRecipeBtn.addEventListener('click', async () => {
        if (!currentFavorite) return;
        
        try {
            const recipe = await api.extractRecipe(currentFavorite.id);
            await navigator.clipboard.writeText(JSON.stringify(recipe, null, 2));
            copyRecipeBtn.textContent = '[OK] Copied';
            setTimeout(() => {
                copyRecipeBtn.textContent = 'Copy Recipe';
            }, 2000);
        } catch (err) {
            alert(`Failed to copy: ${err.message}`);
        }
    });

    // Delete favorite
    deleteBtn.addEventListener('click', async () => {
        if (!currentFavorite) return;
        
        if (!confirm('Are you sure you want to remove this favorite?')) return;
        
        try {
            await api.removeFavorite(currentFavorite.id);
            favoriteModal.classList.add('hidden');
            
            // Remove from grid
            const item = galleryGrid.querySelector(`[data-id="${currentFavorite.id}"]`);
            if (item) {
                item.remove();
            }
            
            // Remove from array
            allFavorites = allFavorites.filter(f => f.id !== currentFavorite.id);
            
            if (allFavorites.length === 0) {
                galleryGrid.innerHTML = '<div class="empty-state">No favorites yet.</div>';
            }
        } catch (err) {
            alert(`Failed to delete: ${err.message}`);
        }
    });

    // Regenerate
    regenBtn.addEventListener('click', async () => {
        if (!currentFavorite) return;
        
        try {
            const recipe = await api.extractRecipe(currentFavorite.id);
            sessionStorage.setItem('pendingRecipe', JSON.stringify(recipe));
            window.location.href = '/?from=gallery';
        } catch (err) {
            alert(`Failed to get recipe: ${err.message}`);
        }
    });

    // Keyboard shortcut
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !favoriteModal.classList.contains('hidden')) {
            favoriteModal.classList.add('hidden');
        }
    });

    // Initialize
    loadFavorites();
});
