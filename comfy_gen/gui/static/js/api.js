/**
 * API client for ComfyGen backend
 */

const API_BASE = '';

class ComfyGenAPI {
    constructor() {
        this.baseUrl = API_BASE;
    }

    async request(endpoint, options = {}) {
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
        return this.request('/api/health');
    }

    // Categories
    async listCategories(type = null) {
        let endpoint = '/api/categories';
        if (type) {
            endpoint += `?type=${type}`;
        }
        return this.request(endpoint);
    }

    async getCategory(id) {
        return this.request(`/api/categories/${id}`);
    }

    async searchCategories(query) {
        return this.request(`/api/categories/search?q=${encodeURIComponent(query)}`);
    }

    // Recipes
    async listRecipes(categoryId = null, limit = 20) {
        let endpoint = `/api/recipes?limit=${limit}`;
        if (categoryId) {
            endpoint += `&category_id=${categoryId}`;
        }
        return this.request(endpoint);
    }

    async getRecipe(id) {
        return this.request(`/api/recipes/${id}`);
    }

    // Compose
    async compose(text, policyTier = 'explicit', explain = true) {
        return this.request('/api/compose', {
            method: 'POST',
            body: JSON.stringify({
                text,
                policy_tier: policyTier,
                explain,
            }),
        });
    }

    async previewCompose(text, policyTier = 'explicit') {
        return this.request('/api/compose/preview', {
            method: 'POST',
            body: JSON.stringify({
                text,
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

        return this.request('/api/generate', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    // Favorites
    async listFavorites(limit = 50, offset = 0) {
        return this.request(`/api/favorites?limit=${limit}&offset=${offset}`);
    }

    async markFavorite(data) {
        return this.request('/api/favorites', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async removeFavorite(id) {
        return this.request(`/api/favorites/${id}`, {
            method: 'DELETE',
        });
    }

    async extractRecipe(favoriteId) {
        return this.request(`/api/favorites/${favoriteId}/recipe`);
    }

    // Workflows
    async listWorkflows() {
        return this.request('/api/workflows');
    }

    async getWorkflow(name) {
        return this.request(`/api/workflows/${name}`);
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
