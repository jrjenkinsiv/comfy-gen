/**
 * API client for ComfyGen backend
 */

const API_BASE = '/api/v1';

class ComfyGenAPI {
    constructor() {
        this.baseUrl = API_BASE;
    }

    async request(endpoint, options = {}) {
        // Build full URL - always prepend baseUrl for relative paths
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (err) {
            console.error(`API Error [${endpoint}]:`, err);
            throw err;
        }
    }

    // Health check
    async health() {
        return this.request('/health');
    }

    // Categories
    async listCategories(type = null) {
        let endpoint = '/categories';
        if (type) {
            endpoint += `?type=${type}`;
        }
        const response = await this.request(endpoint);
        // API returns {items: [...], total: ...}, extract and normalize items
        const items = response.items || response;
        return items.map(cat => ({
            ...cat,
            name: cat.display_name || cat.name || cat.id,
            // Flatten keywords for search - API returns {primary: [], secondary: [], specific: []}
            keywords: [
                ...(cat.keywords?.primary || []),
                ...(cat.keywords?.secondary || []),
                ...(cat.keywords?.specific || [])
            ]
        }));
    }

    async getCategory(id) {
        return this.request(`/categories/${id}`);
    }

    async searchCategories(query) {
        return this.request(`/categories/search?q=${encodeURIComponent(query)}`);
    }

    // Recipes
    async listRecipes(categoryId = null, limit = 20) {
        let endpoint = `/recipes?limit=${limit}`;
        if (categoryId) {
            endpoint += `&category_id=${categoryId}`;
        }
        return this.request(endpoint);
    }

    async getRecipe(id) {
        return this.request(`/recipes/${id}`);
    }

    // Compose
    async compose(input, policyTier = 'general', explain = true) {
        return this.request('/compose', {
            method: 'POST',
            body: JSON.stringify({
                input,
                policy_tier: policyTier,
                dry_run: false,
            }),
        });
    }

    async previewCompose(input, policyTier = 'general') {
        return this.request('/compose/preview', {
            method: 'POST',
            body: JSON.stringify({
                input,
                policy_tier: policyTier,
            }),
        });
    }

    // Generation
    async generate(recipe, settings = {}) {
        const payload = {
            prompt: recipe.prompt || '',
            negative_prompt: recipe.negative_prompt || '',
            width: settings.width || 768,
            height: settings.height || 1024,
            steps: settings.steps || 50,
            cfg: settings.cfg || 8.5,
            seed: settings.seed || -1,
            loras: recipe.loras || [],
            checkpoint: recipe.checkpoint || null,
            workflow: settings.workflow || null,
        };

        return this.request('/generate', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    // Favorites
    async listFavorites(limit = 50, offset = 0) {
        return this.request(`/favorites?limit=${limit}&offset=${offset}`);
    }

    async markFavorite(data) {
        return this.request('/favorites', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async removeFavorite(id) {
        return this.request(`/favorites/${id}`, {
            method: 'DELETE',
        });
    }

    async extractRecipe(favoriteId) {
        return this.request(`/favorites/${favoriteId}/extract-recipe`);
    }

    // Workflows
    async listWorkflows() {
        return this.request('/workflows');
    }

    async getWorkflow(name) {
        return this.request(`/workflows/${name}`);
    }
}

// Export singleton
const api = new ComfyGenAPI();

// WebSocket for progress updates
class ProgressSocket {
    constructor() {
        this.ws = null;
        this.listeners = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnects = 5;
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/progress`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.emit('connected', {});
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.emit('disconnected', {});
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.emit(data.type || 'message', data);
                } catch (err) {
                    console.error('Failed to parse WebSocket message:', err);
                }
            };
        } catch (err) {
            console.error('Failed to create WebSocket:', err);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnects) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay}ms...`);
            setTimeout(() => this.connect(), delay);
        }
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => callback(data));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

const progressSocket = new ProgressSocket();
