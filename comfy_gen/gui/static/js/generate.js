/**
 * Main generation page logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generate-form');
    const promptInput = document.getElementById('prompt');
    const negativeInput = document.getElementById('negative-prompt');
    const widthInput = document.getElementById('width');
    const heightInput = document.getElementById('height');
    const stepsInput = document.getElementById('steps');
    const cfgInput = document.getElementById('cfg');
    const seedInput = document.getElementById('seed');
    const workflowSelect = document.getElementById('workflow');
    
    const generateBtn = document.getElementById('generate-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressStep = document.getElementById('progress-step');
    
    const resultContainer = document.getElementById('result-container');
    const resultImage = document.getElementById('result-image');
    const favoriteBtn = document.getElementById('favorite-btn');
    const copyPromptBtn = document.getElementById('copy-prompt-btn');
    const downloadBtn = document.getElementById('download-btn');
    const regenerateBtn = document.getElementById('regenerate-btn');
    
    const statusDot = document.getElementById('status-dot');

    let currentGeneration = null;
    let isGenerating = false;

    // Load workflows
    async function loadWorkflows() {
        try {
            const workflows = await api.listWorkflows();
            workflowSelect.innerHTML = '<option value="">Auto-select</option>';
            workflows.forEach(wf => {
                const option = document.createElement('option');
                option.value = wf.name;
                option.textContent = wf.name;
                workflowSelect.appendChild(option);
            });
        } catch (err) {
            console.error('Failed to load workflows:', err);
        }
    }

    // Connect WebSocket for progress
    progressSocket.connect();

    progressSocket.on('connected', () => {
        statusDot.classList.add('connected');
        statusDot.classList.remove('disconnected');
    });

    progressSocket.on('disconnected', () => {
        statusDot.classList.remove('connected');
        statusDot.classList.add('disconnected');
    });

    progressSocket.on('progress', (data) => {
        if (isGenerating) {
            const percent = Math.round((data.value / data.max) * 100);
            progressFill.style.width = `${percent}%`;
            progressText.textContent = `${percent}%`;
            progressStep.textContent = data.step || 'Processing...';
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

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (isGenerating) return;

        startGeneration();

        const recipe = {
            prompt: promptInput.value.trim(),
            negative_prompt: negativeInput.value.trim(),
        };

        const settings = {
            width: parseInt(widthInput.value) || 768,
            height: parseInt(heightInput.value) || 1024,
            steps: parseInt(stepsInput.value) || 50,
            cfg: parseFloat(cfgInput.value) || 8.5,
            seed: parseInt(seedInput.value) || -1,
            workflow: workflowSelect.value || null,
        };

        try {
            const result = await api.generate(recipe, settings);
            currentGeneration = {
                ...result,
                recipe,
                settings,
            };
            finishGeneration(result);
        } catch (err) {
            handleError(err.message);
        }
    });

    function startGeneration() {
        isGenerating = true;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="btn-spinner"></span> Generating...';
        cancelBtn.classList.remove('hidden');
        progressContainer.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        progressStep.textContent = 'Starting...';
    }

    function finishGeneration(result) {
        isGenerating = false;
        generateBtn.disabled = false;
        generateBtn.innerHTML = 'Generate';
        cancelBtn.classList.add('hidden');
        progressContainer.classList.add('hidden');
        progressFill.style.width = '100%';
        
        if (result.image_url) {
            resultImage.src = result.image_url;
            resultContainer.classList.remove('hidden');
            downloadBtn.href = result.image_url;
            downloadBtn.download = result.filename || 'generated.png';
        }
    }

    function handleError(message) {
        isGenerating = false;
        generateBtn.disabled = false;
        generateBtn.innerHTML = 'Generate';
        cancelBtn.classList.add('hidden');
        progressContainer.classList.add('hidden');
        alert(`Generation failed: ${message}`);
    }

    // Cancel button
    cancelBtn.addEventListener('click', () => {
        // TODO: Implement cancel via API
        handleError('Generation cancelled');
    });

    // Favorite button
    favoriteBtn.addEventListener('click', async () => {
        if (!currentGeneration) return;

        try {
            await api.markFavorite({
                image_url: currentGeneration.image_url,
                recipe: currentGeneration.recipe,
                settings: currentGeneration.settings,
            });
            favoriteBtn.textContent = '[OK] Saved';
            favoriteBtn.disabled = true;
        } catch (err) {
            alert(`Failed to save favorite: ${err.message}`);
        }
    });

    // Copy prompt button
    copyPromptBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(promptInput.value).then(() => {
            copyPromptBtn.textContent = '[OK] Copied';
            setTimeout(() => {
                copyPromptBtn.textContent = 'Copy Prompt';
            }, 2000);
        });
    });

    // Regenerate button
    regenerateBtn.addEventListener('click', () => {
        // Trigger form submit
        form.dispatchEvent(new Event('submit'));
    });

    // Initialize
    loadWorkflows();
});
