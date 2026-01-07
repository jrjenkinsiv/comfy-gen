/**
 * Intelligent Composition page logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('compose-form');
    const textInput = document.getElementById('compose-text');
    const policySelect = document.getElementById('policy-tier');
    
    const previewBtn = document.getElementById('preview-btn');
    const composeBtn = document.getElementById('compose-btn');
    const generateBtn = document.getElementById('generate-btn');
    
    const previewContainer = document.getElementById('preview-container');
    const explanationContainer = document.getElementById('explanation-container');
    const recipeContainer = document.getElementById('recipe-container');
    const recipeJson = document.getElementById('recipe-json');
    
    // Explanation elements
    const explanationSummary = document.getElementById('explanation-summary');
    const categoriesUsed = document.getElementById('categories-used');
    const stepsTimeline = document.getElementById('steps-timeline');
    const warningsList = document.getElementById('warnings-list');
    const warningsSection = document.getElementById('warnings-section');
    const suggestionsList = document.getElementById('suggestions-list');
    const suggestionsSection = document.getElementById('suggestions-section');
    
    // Modal elements
    const recipeModal = document.getElementById('recipe-modal');
    const modalClose = document.getElementById('modal-close');
    const viewRecipeBtn = document.getElementById('view-recipe-btn');
    
    let currentComposition = null;

    // Preview button - just shows explanation
    previewBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();
        if (!text) {
            alert('Please enter a description');
            return;
        }

        previewBtn.disabled = true;
        previewBtn.innerHTML = '<span class="btn-spinner"></span> Analyzing...';

        try {
            const result = await api.previewCompose(text, policySelect.value);
            displayExplanation(result.explanation);
            previewContainer.classList.remove('hidden');
            explanationContainer.classList.remove('hidden');
            recipeContainer.classList.add('hidden');
        } catch (err) {
            alert(`Preview failed: ${err.message}`);
        } finally {
            previewBtn.disabled = false;
            previewBtn.innerHTML = 'Preview';
        }
    });

    // Compose button - generates recipe
    composeBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();
        if (!text) {
            alert('Please enter a description');
            return;
        }

        composeBtn.disabled = true;
        composeBtn.innerHTML = '<span class="btn-spinner"></span> Composing...';

        try {
            const result = await api.compose(text, policySelect.value, true);
            currentComposition = result;
            
            displayExplanation(result.explanation);
            displayRecipe(result.recipe);
            
            previewContainer.classList.remove('hidden');
            explanationContainer.classList.remove('hidden');
            recipeContainer.classList.remove('hidden');
            generateBtn.classList.remove('hidden');
        } catch (err) {
            alert(`Composition failed: ${err.message}`);
        } finally {
            composeBtn.disabled = false;
            composeBtn.innerHTML = 'Compose Recipe';
        }
    });

    // Generate button - uses composed recipe
    generateBtn.addEventListener('click', () => {
        if (!currentComposition || !currentComposition.recipe) {
            alert('No recipe to generate');
            return;
        }

        // Store recipe in sessionStorage and navigate to generate page
        sessionStorage.setItem('pendingRecipe', JSON.stringify(currentComposition.recipe));
        window.location.href = '/?from=compose';
    });

    // View recipe modal
    viewRecipeBtn.addEventListener('click', () => {
        if (currentComposition && currentComposition.recipe) {
            recipeJson.textContent = JSON.stringify(currentComposition.recipe, null, 2);
            recipeModal.classList.remove('hidden');
        }
    });

    modalClose.addEventListener('click', () => {
        recipeModal.classList.add('hidden');
    });

    recipeModal.addEventListener('click', (e) => {
        if (e.target === recipeModal) {
            recipeModal.classList.add('hidden');
        }
    });

    function displayExplanation(explanation) {
        if (!explanation) return;

        // Summary
        explanationSummary.textContent = explanation.summary || 'Recipe composed successfully';

        // Categories used
        categoriesUsed.innerHTML = '';
        if (explanation.categories_used) {
            explanation.categories_used.forEach(cat => {
                const pill = document.createElement('span');
                pill.className = `category-pill ${cat.source || 'inferred'}`;
                pill.innerHTML = `
                    ${cat.id || cat.name}
                    ${cat.confidence ? `<span class="confidence">${Math.round(cat.confidence * 100)}%</span>` : ''}
                `;
                categoriesUsed.appendChild(pill);
            });
        }

        // Steps timeline
        stepsTimeline.innerHTML = '';
        if (explanation.steps) {
            explanation.steps.forEach(step => {
                const item = document.createElement('div');
                item.className = 'step-item';
                item.innerHTML = `
                    <div class="phase">${step.phase}</div>
                    <div class="detail">${step.detail}</div>
                `;
                stepsTimeline.appendChild(item);
            });
        }

        // Warnings
        if (explanation.warnings && explanation.warnings.length > 0) {
            warningsSection.classList.remove('hidden');
            warningsList.innerHTML = '';
            explanation.warnings.forEach(warning => {
                const li = document.createElement('li');
                li.textContent = warning;
                warningsList.appendChild(li);
            });
        } else {
            warningsSection.classList.add('hidden');
        }

        // Suggestions
        if (explanation.suggestions && explanation.suggestions.length > 0) {
            suggestionsSection.classList.remove('hidden');
            suggestionsList.innerHTML = '';
            explanation.suggestions.forEach(suggestion => {
                const li = document.createElement('li');
                li.textContent = suggestion;
                suggestionsList.appendChild(li);
            });
        } else {
            suggestionsSection.classList.add('hidden');
        }
    }

    function displayRecipe(recipe) {
        if (!recipe) return;

        // Show a preview of the composed recipe
        const preview = {
            prompt: recipe.prompt ? recipe.prompt.substring(0, 100) + '...' : '',
            loras: recipe.loras || [],
            checkpoint: recipe.checkpoint || 'auto',
        };

        recipeJson.textContent = JSON.stringify(preview, null, 2);
    }

    // Check for pending recipe from compose page
    const pendingRecipe = sessionStorage.getItem('pendingRecipe');
    if (pendingRecipe) {
        try {
            const recipe = JSON.parse(pendingRecipe);
            sessionStorage.removeItem('pendingRecipe');
            // TODO: Pre-fill the form with the composed recipe
            console.log('Loaded pending recipe:', recipe);
        } catch (err) {
            console.error('Failed to load pending recipe:', err);
        }
    }
});
