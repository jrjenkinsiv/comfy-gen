/**
 * Intelligent Composition page logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('compose-input');
    const policySelect = document.getElementById('policy-tier');
    
    const previewBtn = document.getElementById('preview-btn');
    const composeBtn = document.getElementById('compose-btn');
    
    const explanationBlock = document.getElementById('explanation-block');
    const emptyExplanation = document.getElementById('empty-explanation');
    const recipeCard = document.getElementById('recipe-card');
    const recipeJson = document.getElementById('recipe-json');
    
    // Explanation elements
    const explanationSummary = document.getElementById('explanation-summary');
    const categoryPills = document.getElementById('category-pills');
    const stepsTimeline = document.getElementById('steps-timeline');
    const warningsList = document.getElementById('warnings-list');
    const warningsSection = document.getElementById('warnings-section');
    
    let currentComposition = null;

    // Guard against missing elements
    if (!previewBtn || !textInput) {
        console.error('Required compose elements not found');
        return;
    }

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
            const result = await api.previewCompose(text, policySelect?.value || 'general');
            displayPreview(result);
            if (explanationBlock) explanationBlock.classList.remove('hidden');
            if (emptyExplanation) emptyExplanation.classList.add('hidden');
        } catch (err) {
            alert('Preview failed: ' + err.message);
        } finally {
            previewBtn.disabled = false;
            previewBtn.innerHTML = 'Preview';
        }
    });

    // Compose button - generates recipe
    if (composeBtn) {
        composeBtn.addEventListener('click', async () => {
            const text = textInput.value.trim();
            if (!text) {
                alert('Please enter a description');
                return;
            }

            composeBtn.disabled = true;
            composeBtn.innerHTML = '<span class="btn-spinner"></span> Composing...';

            try {
                const result = await api.compose(text, policySelect?.value || 'general', true);
                currentComposition = result;
                
                displayComposition(result);
                if (explanationBlock) explanationBlock.classList.remove('hidden');
                if (emptyExplanation) emptyExplanation.classList.add('hidden');
                if (recipeCard) recipeCard.style.display = 'block';
            } catch (err) {
                alert('Composition failed: ' + err.message);
            } finally {
                composeBtn.disabled = false;
                composeBtn.innerHTML = 'Compose & Generate';
            }
        });
    }

    function displayPreview(result) {
        // Display explicit categories
        if (categoryPills) {
            categoryPills.innerHTML = '';
            (result.explicit_categories || []).forEach(cat => {
                const pill = document.createElement('span');
                pill.className = 'category-pill ' + (cat.type || 'subject');
                pill.textContent = cat.display_name || cat.id;
                categoryPills.appendChild(pill);
            });
            
            // Add inferred categories
            (result.inferred_categories || []).forEach(cat => {
                const pill = document.createElement('span');
                pill.className = 'category-pill inferred';
                pill.textContent = (cat.id || cat) + ' (inferred)';
                categoryPills.appendChild(pill);
            });
        }
        
        if (explanationSummary) {
            explanationSummary.textContent = 'Found ' + result.total_categories + ' categories. Remaining prompt: "' + result.remaining_prompt + '"';
        }
    }

    function displayComposition(result) {
        // Show explanation
        if (explanationSummary && result.explanation) {
            explanationSummary.textContent = result.explanation.summary;
        }
        
        // Show categories as pills
        if (categoryPills && result.explanation) {
            categoryPills.innerHTML = '';
            (result.explanation.final_categories || []).forEach(catId => {
                const pill = document.createElement('span');
                pill.className = 'category-pill';
                pill.textContent = catId;
                categoryPills.appendChild(pill);
            });
        }
        
        // Show steps timeline
        if (stepsTimeline && result.explanation) {
            stepsTimeline.innerHTML = '';
            (result.explanation.steps || []).forEach(step => {
                const stepEl = document.createElement('div');
                stepEl.className = 'step step-' + step.phase;
                stepEl.innerHTML = '<span class="step-phase">' + step.phase + '</span>' +
                    '<span class="step-action">' + step.action + '</span>' +
                    '<span class="step-detail">' + step.detail + '</span>';
                stepsTimeline.appendChild(stepEl);
            });
        }
        
        // Show warnings
        if (warningsSection && warningsList && result.explanation) {
            const warnings = result.explanation.warnings || [];
            if (warnings.length > 0) {
                warningsSection.classList.remove('hidden');
                warningsList.innerHTML = warnings.map(function(w) { return '<li>' + w + '</li>'; }).join('');
            } else {
                warningsSection.classList.add('hidden');
            }
        }
        
        // Show recipe JSON
        if (recipeJson && result.recipe) {
            recipeJson.textContent = JSON.stringify(result.recipe, null, 2);
        }
    }
});
