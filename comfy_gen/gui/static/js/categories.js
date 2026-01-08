/**
 * Categories browser page logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const categoriesGrid = document.getElementById('categories-grid');
    const typeFilter = document.getElementById('type-filter');
    const searchInput = document.getElementById('search-input');
    const categoryModal = document.getElementById('category-detail-modal');
    const modalClose = categoryModal?.querySelector('.modal-close');
    
    // Modal content elements
    const modalTitle = document.getElementById('modal-title');
    const modalType = document.getElementById('modal-type');
    const modalDescription = document.getElementById('modal-description');
    const modalKeywords = document.getElementById('modal-keywords');
    const modalRecipes = document.getElementById('modal-recipes');
    const useCategory = document.getElementById('use-category');
    
    let allCategories = [];
    let currentCategory = null;

    // Load categories
    async function loadCategories(type = null) {
        try {
            categoriesGrid.innerHTML = '<div class="loading-state">Loading categories...</div>';
            const categories = await api.listCategories(type);
            allCategories = categories;
            renderCategories(categories);
        } catch (err) {
            categoriesGrid.innerHTML = `<div class="empty-state">Failed to load categories: ${err.message}</div>`;
        }
    }

    function renderCategories(categories) {
        if (!categories || categories.length === 0) {
            categoriesGrid.innerHTML = '<div class="empty-state">No categories found</div>';
            return;
        }

        categoriesGrid.innerHTML = '';
        categories.forEach(category => {
            const card = createCategoryCard(category);
            categoriesGrid.appendChild(card);
        });
    }

    function createCategoryCard(category) {
        const card = document.createElement('div');
        card.className = 'category-card';
        card.dataset.id = category.id;
        
        const typeClass = (category.type || 'modifier').toLowerCase();
        const keywords = category.keywords || [];
        const keywordPreview = keywords.slice(0, 5).join(', ');
        
        card.innerHTML = `
            <span class="type-badge ${typeClass}">${category.type || 'modifier'}</span>
            <h3>${category.name || category.id}</h3>
            <p class="keywords">${keywordPreview}${keywords.length > 5 ? '...' : ''}</p>
        `;
        
        card.addEventListener('click', () => openCategoryModal(category));
        
        return card;
    }

    async function openCategoryModal(category) {
        currentCategory = category;
        
        modalTitle.textContent = category.name || category.id;
        modalType.textContent = category.type || 'modifier';
        modalType.className = `type-badge ${(category.type || 'modifier').toLowerCase()}`;
        modalDescription.textContent = category.description || 'No description available';
        
        // Keywords
        modalKeywords.innerHTML = '';
        (category.keywords || []).forEach(kw => {
            const span = document.createElement('span');
            span.className = 'keyword-tag';
            span.textContent = kw;
            modalKeywords.appendChild(span);
        });
        
        // Load recipes for this category
        modalRecipes.innerHTML = '<div class="loading-state">Loading recipes...</div>';
        
        try {
            const recipes = await api.listRecipes(category.id, 10);
            if (recipes && recipes.length > 0) {
                modalRecipes.innerHTML = '';
                recipes.forEach(recipe => {
                    const item = document.createElement('div');
                    item.className = 'recipe-item';
                    item.innerHTML = `
                        <strong>${recipe.name || recipe.id}</strong>
                        <span>${recipe.description || ''}</span>
                    `;
                    modalRecipes.appendChild(item);
                });
            } else {
                modalRecipes.innerHTML = '<div class="empty-state">No recipes in this category</div>';
            }
        } catch (err) {
            modalRecipes.innerHTML = `<div class="empty-state">Failed to load recipes</div>`;
        }
        
        categoryModal.classList.remove('hidden');
    }

    // Type filter
    if (typeFilter) {
        typeFilter.addEventListener('change', () => {
            const type = typeFilter.value || null;
            loadCategories(type);
        });
    }

    // Search
    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = searchInput.value.trim().toLowerCase();
                if (!query) {
                    renderCategories(allCategories);
                } else {
                    const filtered = allCategories.filter(cat => 
                        (cat.name || cat.id).toLowerCase().includes(query) ||
                        (cat.keywords || []).some(kw => kw.toLowerCase().includes(query))
                    );
                    renderCategories(filtered);
                }
            }, 300);
        });
    }

    // Modal close
    if (modalClose) {
        modalClose.addEventListener('click', () => {
            categoryModal.classList.add('hidden');
        });
    }

    if (categoryModal) {
        categoryModal.addEventListener('click', (e) => {
            if (e.target === categoryModal) {
                categoryModal.classList.add('hidden');
            }
        });
    }

    // Use category button
    if (useCategory) {
        useCategory.addEventListener('click', () => {
            if (currentCategory) {
                // Store in sessionStorage and navigate to compose
                sessionStorage.setItem('selectedCategory', JSON.stringify(currentCategory));
                window.location.href = '/compose';
            }
        });
    }

    // Add keyboard shortcut to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && categoryModal && !categoryModal.classList.contains('hidden')) {
            categoryModal.classList.add('hidden');
        }
    });

    // Initialize
    loadCategories();
});
