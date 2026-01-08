/**
 * Main generation page logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Input elements - match HTML IDs
    const promptInput = document.getElementById('prompt-input');
    const negativeInput = document.getElementById('negative-input');
    const widthInput = document.getElementById('width');
    const heightInput = document.getElementById('height');
    const stepsInput = document.getElementById('steps');
    const cfgInput = document.getElementById('cfg');
    const seedInput = document.getElementById('seed');
    const workflowSelect = document.getElementById('workflow');
    
    // Buttons
    const generateBtn = document.getElementById('generate-btn');
    
    // Progress elements
    const progressSection = document.getElementById('progress-section');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    // Result elements
    const resultSection = document.getElementById('result-section');
    const emptyState = document.getElementById('empty-state');
    const resultImage = document.getElementById('result-image');
    const favoriteBtn = document.getElementById('favorite-btn');
    const downloadLink = document.getElementById('download-link');
    const copyUrlBtn = document.getElementById('copy-url-btn');
    
    // Status
    const statusDot = document.getElementById('status-dot');

    let currentGeneration = null;
    let isGenerating = false;

    // Guard against missing elements
    if (!generateBtn || !promptInput) {
        console.error('Required generate elements not found');
        return;
    }

    // Connect WebSocket for progress (if available)
    if (typeof progressSocket !== 'undefined') {
        progressSocket.connect();

        progressSocket.on('connected', () => {
            if (statusDot) {
                statusDot.classList.add('connected');
                statusDot.classList.remove('disconnected');
            }
        });

        progressSocket.on('disconnected', () => {
            if (statusDot) {
                statusDot.classList.remove('connected');
                statusDot.classList.add('disconnected');
            }
        });

        progressSocket.on('progress', (data) => {
            if (isGenerating && progressFill && progressText) {
                const percent = Math.round((data.value / data.max) * 100);
                progressFill.style.width = percent + '%';
                progressText.textContent = percent + '%';
            }
        });

        progressSocket.on('complete', (data) => {
            if (isGenerating) {
                finishGeneration(data);
            }
        });

        progressSocket.on('error', (data) => {
            if (isGenerating) {
                handleError(data.message || 'Generation failed');
            }
        });
    }

    // Generate button click
    generateBtn.addEventListener('click', async () => {
        if (isGenerating) return;

        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert('Please enter a prompt');
            return;
        }

        startGeneration();

        try {
            const result = await api.generate({
                prompt: prompt,
                negative_prompt: negativeInput?.value.trim() || '',
                workflow: workflowSelect?.value || 'flux-dev.json',
                steps: parseInt(stepsInput?.value) || 30,
                cfg: parseFloat(cfgInput?.value) || 7.5,
                width: parseInt(widthInput?.value) || 1024,
                height: parseInt(heightInput?.value) || 1024,
                seed: parseInt(seedInput?.value) || -1,
            });

            finishGeneration(result);
        } catch (err) {
            handleError(err.message);
        }
    });

    function startGeneration() {
        isGenerating = true;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="btn-spinner"></span> Generating...';
        
        if (progressSection) progressSection.classList.remove('hidden');
        if (emptyState) emptyState.classList.add('hidden');
        if (resultSection) resultSection.classList.add('hidden');
        if (progressFill) progressFill.style.width = '0%';
        if (progressText) progressText.textContent = 'Starting...';
    }

    function finishGeneration(result) {
        isGenerating = false;
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<span class="btn-text">Generate</span>';
        
        if (progressSection) progressSection.classList.add('hidden');
        
        currentGeneration = result;
        
        if (result.image_url && resultImage) {
            resultImage.src = result.image_url;
            if (downloadLink) {
                downloadLink.href = result.image_url;
                downloadLink.download = result.filename || 'generated.png';
            }
            if (resultSection) resultSection.classList.remove('hidden');
        }
    }

    function handleError(message) {
        isGenerating = false;
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<span class="btn-text">Generate</span>';
        
        if (progressSection) progressSection.classList.add('hidden');
        if (emptyState) emptyState.classList.remove('hidden');
        
        alert('Generation failed: ' + message);
    }

    // Favorite button
    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', async () => {
            if (!currentGeneration) return;
            
            try {
                await api.addFavorite(currentGeneration);
                favoriteBtn.innerHTML = '<span>★</span> Favorited';
                favoriteBtn.classList.add('favorited');
            } catch (err) {
                alert('Failed to add favorite: ' + err.message);
            }
        });
    }

    // Copy URL button
    if (copyUrlBtn) {
        copyUrlBtn.addEventListener('click', () => {
            if (!currentGeneration?.image_url) return;
            
            navigator.clipboard.writeText(currentGeneration.image_url).then(() => {
                copyUrlBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyUrlBtn.textContent = 'Copy URL';
                }, 2000);
            });
        });
    }
});
