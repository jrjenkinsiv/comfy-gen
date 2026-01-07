# Testing & Verification Guide

**Last updated:** 2026-01-07

This guide provides procedures for testing all components of the Intelligent Generation System.

## Table of Contents

- [Quick Start](#quick-start)
- [Server Setup](#server-setup)
- [Category System Tests](#category-system-tests)
- [Parser Tests](#parser-tests)
- [API Endpoint Tests](#api-endpoint-tests)
- [Web GUI Tests](#web-gui-tests)
- [MLflow Integration Tests](#mlflow-integration-tests)
- [End-to-End Tests](#end-to-end-tests)

---

## Quick Start

```bash
# 1. Start the API server
cd /Users/jrjenkinsiv/Development/comfy-gen
uvicorn comfy_gen.api.app:app --reload --host 0.0.0.0 --port 8000

# 2. Verify health
curl http://localhost:8000/health | jq

# 3. Open web GUI
open http://localhost:8000/gui
```

---

## Server Setup

### Starting the API Server

```bash
cd /Users/jrjenkinsiv/Development/comfy-gen

# Development mode with auto-reload
uvicorn comfy_gen.api.app:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn comfy_gen.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify Server Health

```bash
# Basic health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Interactive API Docs

Access Swagger UI for interactive testing:
```
http://localhost:8000/docs
```

Or ReDoc:
```
http://localhost:8000/redoc
```

---

## Category System Tests

### Test 1: Schema Validation

Validates all category YAML files against the JSON Schema.

```bash
cd /Users/jrjenkinsiv/Development/comfy-gen

python3 -c "
from comfy_gen.categories.validator import validate_all_categories

errors = validate_all_categories()
if not errors:
    print('[OK] All categories valid')
else:
    for path, errs in errors.items():
        if errs:
            print(f'[ERROR] {path}: {errs}')
"
```

**Expected:** `[OK] All categories valid`

### Test 2: Registry Loading

Verifies categories load into the registry.

```bash
python3 -c "
from comfy_gen.categories.registry import CategoryRegistry

registry = CategoryRegistry.get_instance()
print(f'[OK] Loaded {len(registry.list_all())} categories')

for cat in registry.list_all()[:5]:
    print(f'  - {cat.id}: {cat.display_name} ({cat.type.value})')
"
```

**Expected:** Lists categories with IDs, names, and types.

### Test 3: Category Lookup

```bash
python3 -c "
from comfy_gen.categories.registry import CategoryRegistry

registry = CategoryRegistry.get_instance()

# Test by ID
cat = registry.get('portrait')
if cat:
    print(f'[OK] Found: {cat.display_name}')
    print(f'  Keywords: {cat.keywords.primary}')
else:
    print('[WARN] portrait category not found')
"
```

### Test 4: Category Filtering

```bash
python3 -c "
from comfy_gen.categories.registry import CategoryRegistry
from comfy_gen.api.schemas.category import CategoryType

registry = CategoryRegistry.get_instance()

# Filter by type
subjects = registry.get_by_type(CategoryType.SUBJECT)
print(f'[OK] Found {len(subjects)} subject categories')

# Filter by policy tier
general = registry.get_by_policy_tier('general')
print(f'[OK] Found {len(general)} general-tier categories')
"
```

---

## Parser Tests

### Test 5: Tag Parser

Tests @tag syntax extraction.

```bash
python3 -c "
from comfy_gen.parsing.tag_parser import TagParser
from comfy_gen.categories.registry import CategoryRegistry

registry = CategoryRegistry.get_instance()
parser = TagParser(registry)

# Test tag parsing
result = parser.parse('@portrait @night professional headshot')

print('[OK] Tag Parser Results:')
print(f'  Tags found: {[m.category_id for m in result.matches]}')
print(f'  Remaining text: {result.remaining_text!r}')
print(f'  Valid matches: {result.valid_count}')
"
```

**Expected:** Extracts `portrait`, `night` tags; remaining text is `professional headshot`.

### Test 6: Intent Classifier

Tests keyword-based intent classification.

```bash
python3 -c "
from comfy_gen.parsing.intent_classifier import IntentClassifier
from comfy_gen.categories.registry import CategoryRegistry

registry = CategoryRegistry.get_instance()
classifier = IntentClassifier(registry)

# Test keyword matching
matches = classifier.classify('photo of a woman in Tokyo at night')

print('[OK] Intent Classifier Results:')
for match in matches:
    print(f'  {match.category_id}: {match.confidence:.2f} ({match.matched_keywords})')
"
```

**Expected:** Matches categories like `portrait`, `city`/`japan`, `night` with confidence scores.

### Test 7: Hybrid Parser

Tests combined tag + keyword parsing.

```bash
python3 -c "
from comfy_gen.parsing.intent_classifier import HybridParser
from comfy_gen.categories.registry import CategoryRegistry

registry = CategoryRegistry.get_instance()
parser = HybridParser(registry)

# Test hybrid parsing
result = parser.parse('@portrait woman in city at sunset')

print('[OK] Hybrid Parser Results:')
print(f'  Explicit tags: {result[\"explicit_tags\"]}')
print(f'  Inferred: {[(c.category_id, c.confidence) for c in result[\"inferred_categories\"]]}')
"
```

---

## API Endpoint Tests

### Test 8: Categories API

```bash
# List all categories
curl -s http://localhost:8000/categories | jq '.total'

# Get by type
curl -s "http://localhost:8000/categories?type=subject" | jq '.categories[].id'

# Get specific category
curl -s http://localhost:8000/categories/portrait | jq '.category.display_name'
```

### Test 9: Compose API

```bash
# Basic compose
curl -s -X POST http://localhost:8000/compose \
  -H "Content-Type: application/json" \
  -d '{"input": "@portrait professional headshot"}' | jq

# Preview mode
curl -s -X POST http://localhost:8000/compose/preview \
  -H "Content-Type: application/json" \
  -d '{"input": "woman in city at night"}' | jq

# With policy tier
curl -s -X POST http://localhost:8000/compose \
  -H "Content-Type: application/json" \
  -d '{"input": "@portrait model", "policy_tier": "mature"}' | jq
```

**Expected compose response structure:**
```json
{
  "recipe": {
    "checkpoint": "...",
    "positive_prompt": "...",
    "loras": [...],
    "steps": 50,
    "cfg": 7.5
  },
  "categories_used": ["portrait"],
  "explanation": {
    "summary": "...",
    "steps": [...]
  }
}
```

### Test 10: Favorites API

```bash
# List favorites (requires MLflow)
curl -s http://localhost:8000/favorites | jq

# Mark favorite (requires valid generation_id from MLflow)
curl -s -X POST http://localhost:8000/favorites \
  -H "Content-Type: application/json" \
  -d '{
    "generation_id": "test-run-id",
    "rating": 5,
    "feedback": "Great result"
  }' | jq
```

**Note:** Favorites API requires MLflow to be available. If MLflow is down, you'll get a 503 response.

---

## Web GUI Tests

### Test 11: Access GUI Pages

```bash
# Start server first, then:
open http://localhost:8000/gui           # Main page
open http://localhost:8000/gui/compose   # Compose page
open http://localhost:8000/gui/categories # Categories browser
open http://localhost:8000/gui/gallery   # Favorites gallery
```

### Test 12: Manual GUI Testing

1. **Generate Tab:**
   - Enter a prompt
   - Adjust parameters (steps, CFG)
   - Click Generate
   - Verify progress updates appear
   - Verify image displays on completion

2. **Compose Tab:**
   - Type in the input field
   - Verify @tag highlighting works
   - Click "Preview" to see composition
   - Verify explanation block shows steps
   - Click "Generate" to create image

3. **Categories Tab:**
   - Browse categories list
   - Filter by type (subject/setting/modifier/style)
   - Click a category to view details
   - Verify keywords display correctly

4. **Gallery Tab:**
   - View favorites list (if any)
   - Filter by rating
   - Click to view full image
   - Test "Extract Recipe" button

### Test 13: JavaScript API Client

Open browser console on any GUI page:

```javascript
// Test API client directly
const api = new ComfyGenAPI('http://localhost:8000');

// Get categories
api.getCategories().then(data => console.log('Categories:', data));

// Compose preview
api.composePreview('@portrait woman').then(data => console.log('Preview:', data));
```

---

## MLflow Integration Tests

### Test 14: MLflow Tracker

```bash
python3 -c "
from comfy_gen.tracking.mlflow_tracker import MLflowTracker, MLFLOW_AVAILABLE

print(f'MLflow Available: {MLFLOW_AVAILABLE}')

if MLFLOW_AVAILABLE:
    tracker = MLflowTracker()
    print(f'Tracker Enabled: {tracker.enabled}')
    print(f'Experiment ID: {tracker.experiment_id}')
else:
    print('[WARN] MLflow not available - install with: pip install mlflow')
"
```

### Test 15: Provenance Hashing

```bash
python3 -c "
from comfy_gen.tracking.mlflow_tracker import ProvenanceHashes
from comfy_gen.composition.recipe import Recipe

# Create a test recipe
recipe = Recipe(
    checkpoint='test.safetensors',
    workflow='test.json',
    positive_prompt='test prompt',
    negative_prompt='bad quality',
    loras=[],
    steps=50,
    cfg=7.5,
    width=512,
    height=512,
    sampler='euler',
    scheduler='normal'
)

# Compute hashes
hashes = ProvenanceHashes.from_recipe_and_categories(
    recipe,
    categories_used=['portrait', 'night']
)

print(f'[OK] Recipe Hash: {hashes.recipe_hash[:16]}...')
print(f'[OK] Category Hash: {hashes.category_hash[:16]}...')
"
```

---

## End-to-End Tests

### Test 16: Full Generation Pipeline

This test requires ComfyUI to be running on moira.

```bash
# Check ComfyUI availability first
curl -s http://192.168.1.215:8188/system_stats | jq '.system'

# Then test generation
curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "sunset over mountains",
    "workflow": "flux-dev.json",
    "steps": 20
  }' | jq
```

### Test 17: Compose to Generate Flow

```bash
# Step 1: Compose a recipe
RECIPE=$(curl -s -X POST http://localhost:8000/compose \
  -H "Content-Type: application/json" \
  -d '{"input": "@portrait professional headshot", "dry_run": true}' | jq -r '.recipe')

echo "Recipe: $RECIPE"

# Step 2: Generate with recipe (when generation endpoint accepts recipes)
# This would be: POST /generate with recipe_id
```

---

## Troubleshooting

### Server Won't Start

```bash
# Check for import errors
python3 -c "from comfy_gen.api.app import app; print('OK')"

# Check dependencies
pip install -r requirements.txt
```

### Categories Not Loading

```bash
# Verify definitions directory exists
ls -la comfy_gen/categories/definitions/

# Check YAML syntax
python3 -c "
import yaml
with open('comfy_gen/categories/definitions/subjects/portrait.yaml') as f:
    data = yaml.safe_load(f)
    print(data)
"
```

### MLflow Connection Issues

```bash
# Check MLflow server on cerebro
curl http://192.168.1.162:5001/health

# If unreachable, wake cerebro
ssh cerebro 'printf \"babyseal\\n\" | sudo -S pmset -a displaysleep 0 sleep 0'
```

### GUI Static Files Not Loading

```bash
# Verify static files exist
ls comfy_gen/gui/static/css/
ls comfy_gen/gui/static/js/

# Check mounting in logs when server starts
# Should see: "Mounted GUI static files from ..."
```

---

## See Also

- [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation
- [USAGE.md](USAGE.md) - User guide
- [CATEGORY_AUTHORING.md](CATEGORY_AUTHORING.md) - Creating categories

---

**Documentation Policy:** This is an authoritative testing guide. Add test procedures here, do not create separate test documentation files.
