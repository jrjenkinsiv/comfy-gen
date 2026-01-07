# Category Authoring Guide

**Last updated:** 2026-01-07

This guide explains how to create and edit category YAML files for the Intelligent Generation System.

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Category Types](#category-types)
- [Schema Reference](#schema-reference)
- [Creating a Category](#creating-a-category)
- [Best Practices](#best-practices)
- [Validation](#validation)
- [Examples](#examples)

---

## Overview

Categories define domains of expertise (cars, portraits, anime, etc.) with:
- **Keywords** for natural language detection
- **Prompt fragments** to automatically inject
- **LoRA recommendations** for quality enhancement
- **Generation settings** (steps, CFG, size)
- **Composition rules** for combining categories

Categories live in `comfy_gen/categories/definitions/` organized by type:

```
comfy_gen/categories/definitions/
├── subjects/
│   ├── portrait.yaml
│   ├── car.yaml
│   └── animal.yaml
├── settings/
│   ├── city.yaml
│   └── beach.yaml
├── modifiers/
│   ├── night.yaml
│   └── rainy.yaml
└── styles/
    ├── anime.yaml
    └── photorealistic.yaml
```

---

## File Structure

Each category is a single YAML file with this structure:

```yaml
category:
  id: unique_identifier
  type: subject|setting|modifier|style
  display_name: Human Readable Name
  description: Detailed description of this category
  icon: emoji_or_icon_name
  schema_version: "1.0.0"
  policy_tier: general|mature|explicit

  keywords:
    primary: [...]      # High-confidence matches
    secondary: [...]    # Medium-confidence matches
    specific: [...]     # Exact phrase matches only

  prompts:
    positive_fragments:
      required: [...]   # Always added to prompt
      optional: [...]   # Added if compatible
    negative_fragments:
      required: [...]
      optional: [...]

  loras:
    required: [...]     # Must be used
    recommended: [...]  # Improve quality
    avoid: [...]        # Never use (conflicts)

  settings:
    steps: {min, max, default}
    cfg: {min, max, default}
    size: {width, height, aspect_ratio}
    sampler: string
    scheduler: string

  workflows:
    preferred: [...]           # Use in order
    required_capabilities: []  # Filter workflows
    excluded: []              # Never use

  composition:
    priority: 0-100           # Higher wins conflicts
    conflicts_with: []        # Incompatible categories
    requires: []              # Dependencies
    enhances: []              # Synergy bonuses
    max_per_type: 1           # Limit same-type combinations
```

---

## Category Types

| Type | Role | Examples | Composition Behavior |
|------|------|----------|---------------------|
| `subject` | Main focus | portrait, car, animal, product | Only one primary; others become secondary |
| `setting` | Location/environment | city, beach, forest, studio | Can combine multiple |
| `modifier` | Atmospheric/conditions | night, rainy, foggy, golden-hour | Stack freely |
| `style` | Rendering approach | anime, photorealistic, cinematic | Usually exclusive |

---

## Schema Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique lowercase identifier (`^[a-z][a-z0-9_]*$`) |
| `type` | enum | One of: subject, setting, modifier, style |
| `display_name` | string | Human-readable name for UI |
| `keywords.primary` | array | At least one primary keyword |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `description` | string | null | Detailed description |
| `icon` | string | null | Emoji or icon name |
| `schema_version` | string | "1.0.0" | Schema version |
| `policy_tier` | enum | "general" | general, mature, explicit |

### Keywords

```yaml
keywords:
  primary:
    # High confidence - single word triggers this category
    - portrait
    - headshot
    - face

  secondary:
    # Medium confidence - contextual matching
    - model
    - person
    - woman
    - man

  specific:
    # Exact phrase match only (high precision)
    - close-up portrait
    - studio portrait
    - environmental portrait
```

### Prompt Fragments

```yaml
prompts:
  positive_fragments:
    required:
      # ALWAYS added when category is selected
      - "detailed face"
      - "sharp focus on eyes"
    optional:
      # Added if no conflicts with other categories
      - "soft lighting"
      - "professional photography"

  negative_fragments:
    required:
      # ALWAYS added to negative prompt
      - "blurry"
      - "distorted face"
      - "bad anatomy"
    optional:
      - "cartoon"
      - "anime"
```

### LoRA Specifications

```yaml
loras:
  required:
    # Must be included when category is used
    - filename: essential_style.safetensors
      strength: 0.6

  recommended:
    # Improve quality, auto-selected if available
    - filename: add_detail.safetensors
      strength: 0.4
      trigger_words:
        - "detailed"
    - filename: skin_texture.safetensors
      strength: 0.3
      condition: "if photorealistic"  # Conditional use

  avoid:
    # Never use with this category (conflicts)
    - anime_style.safetensors
    - cartoon_lora.safetensors
```

### Generation Settings

```yaml
settings:
  steps:
    min: 30      # Minimum recommended
    max: 100     # Maximum recommended
    default: 50  # Default value

  cfg:
    min: 6.0
    max: 12.0
    default: 7.5

  size:
    width: 768
    height: 1024
    aspect_ratio: "3:4"  # Portrait orientation

  sampler: euler_ancestral
  scheduler: normal
  denoise: 0.75  # For img2img workflows
```

### Workflow Preferences

```yaml
workflows:
  preferred:
    # Workflows to use, in preference order
    - flux-dev.json
    - pornmaster-pony-stacked-realism.json
    - realistic-vision.json

  required_capabilities:
    # Workflow must support these
    - face_enhancement
    - high_resolution

  excluded:
    # Never use these workflows
    - wan2.2-t2v.json  # Video workflow for image category
```

### Composition Rules

```yaml
composition:
  priority: 70
  # Higher priority wins setting conflicts (0-100)
  # Subject typically 60-80, modifier typically 20-40

  conflicts_with:
    # Categories that cannot be combined
    - underwater  # Portrait + underwater = bad
    - space

  requires:
    # Categories that must also be present
    # (rare, for specialized categories)
    - lighting

  enhances:
    # Categories this works well with (synergy)
    - photorealistic
    - studio

  max_per_type: 1
  # How many of same type can combine
  # 1 = only one subject allowed
```

---

## Creating a Category

### Step 1: Choose Type and ID

```yaml
category:
  id: car              # Lowercase, underscores allowed
  type: subject        # Main focus of image
  display_name: Car
```

### Step 2: Define Keywords

Think about what words users will use:

```yaml
keywords:
  primary:
    - car
    - vehicle
    - automobile
  secondary:
    - drive
    - driving
    - road
    - highway
  specific:
    - sports car
    - vintage car
    - car photography
```

### Step 3: Add Prompt Fragments

What makes a good car image?

```yaml
prompts:
  positive_fragments:
    required:
      - "automotive photography"
      - "clean reflections"
      - "sharp details"
    optional:
      - "studio lighting"
      - "professional car photo"

  negative_fragments:
    required:
      - "duplicate cars"
      - "multiple vehicles"
      - "car show"
      - "parking lot"
    optional:
      - "blurry"
      - "low quality"
```

### Step 4: Configure Settings

Optimal settings for car photography:

```yaml
settings:
  steps:
    min: 30
    max: 80
    default: 50
  cfg:
    min: 6.0
    max: 10.0
    default: 7.5
  size:
    width: 1024
    height: 768
    aspect_ratio: "4:3"  # Landscape for cars
```

### Step 5: Set Composition Rules

How does this combine with other categories?

```yaml
composition:
  priority: 70              # Primary subject
  conflicts_with:
    - underwater
  enhances:
    - city
    - night
    - rain
  max_per_type: 1           # One main vehicle
```

---

## Best Practices

### Keywords

- **Primary keywords** should be unambiguous single words
- **Secondary keywords** provide context but may have other meanings
- **Specific keywords** are multi-word phrases that strongly indicate the category
- Include common synonyms and related terms

### Prompt Fragments

- Keep fragments short and composable
- Use required fragments sparingly (they always appear)
- Optional fragments allow flexibility
- Test that fragments don't conflict when combined

### Settings

- Set reasonable min/max ranges
- Default should work well in most cases
- Consider the category's typical output (portrait = tall, landscape = wide)

### Composition

- Subjects should have priority 60-80
- Settings should have priority 40-60
- Modifiers should have priority 20-40
- Styles can vary based on how exclusive they should be

### Policy Tiers

- `general`: Safe for work, no age restrictions
- `mature`: May contain suggestive content
- `explicit`: Adult content, requires explicit tier access

---

## Validation

### Automated Validation

Categories are validated against the JSON Schema on load:

```bash
# Validate all categories
python3 -c "
from comfy_gen.categories.validator import validate_all_categories
errors = validate_all_categories()
for path, errs in errors.items():
    if errs:
        print(f'{path}: {errs}')
"
```

### Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `'id' does not match pattern` | Invalid ID format | Use lowercase, start with letter |
| `'type' is not one of [...]` | Invalid type | Use: subject, setting, modifier, style |
| `'primary' is a required property` | Missing keywords | Add at least one primary keyword |
| `Additional properties not allowed` | Unknown field | Check spelling, remove extra fields |

### Testing a Category

```python
from comfy_gen.categories.registry import CategoryRegistry
from comfy_gen.parsing.intent_classifier import IntentClassifier

# Load registry (validates on load)
registry = CategoryRegistry.get_instance()

# Check category loaded
cat = registry.get("your_category_id")
print(f"Loaded: {cat.display_name if cat else 'NOT FOUND'}")

# Test keyword matching
classifier = IntentClassifier(registry)
matches = classifier.classify("test prompt with keywords")
for match in matches:
    print(f"  {match.category_id}: {match.confidence:.2f}")
```

---

## Examples

### Subject: Portrait

```yaml
# comfy_gen/categories/definitions/subjects/portrait.yaml
category:
  id: portrait
  type: subject
  display_name: Portrait
  description: Human portrait photography and art
  icon: "person"
  schema_version: "1.0.0"
  policy_tier: general

  keywords:
    primary: [portrait, headshot, face]
    secondary: [model, person, woman, man]
    specific: [close-up portrait, studio portrait]

  prompts:
    positive_fragments:
      required: [detailed face, sharp focus on eyes]
      optional: [soft lighting, professional photography]
    negative_fragments:
      required: [blurry, distorted face, bad anatomy]
      optional: [cartoon, anime]

  loras:
    recommended:
      - filename: add_detail.safetensors
        strength: 0.4

  settings:
    steps: {min: 30, max: 100, default: 50}
    cfg: {min: 6.0, max: 12.0, default: 7.5}
    size: {width: 768, height: 1024, aspect_ratio: "3:4"}

  composition:
    priority: 70
    enhances: [lighting, photorealistic]
    max_per_type: 1
```

### Modifier: Night

```yaml
# comfy_gen/categories/definitions/modifiers/night.yaml
category:
  id: night
  type: modifier
  display_name: Night
  description: Nighttime atmosphere and lighting
  icon: "moon"
  policy_tier: general

  keywords:
    primary: [night, nighttime, dark]
    secondary: [evening, dusk, midnight]
    specific: [night scene, night photography]

  prompts:
    positive_fragments:
      required: [nighttime, dark atmosphere]
      optional: [city lights, moonlight, stars]
    negative_fragments:
      optional: [daylight, bright sun, daytime]

  settings:
    cfg: {default: 8.0}

  composition:
    priority: 30
    conflicts_with: [daylight, golden_hour]
    enhances: [city, car, portrait]
```

### Style: Anime

```yaml
# comfy_gen/categories/definitions/styles/anime.yaml
category:
  id: anime
  type: style
  display_name: Anime
  description: Japanese animation art style
  icon: "art"
  policy_tier: general

  keywords:
    primary: [anime, manga, japanese animation]
    secondary: [cel-shaded, cartoon]
    specific: [anime style, manga art]

  prompts:
    positive_fragments:
      required: [anime style, cel shading]
      optional: [vibrant colors, clean lines]
    negative_fragments:
      required: [photorealistic, 3d render]

  loras:
    recommended:
      - filename: anime_style.safetensors
        strength: 0.7

  workflows:
    preferred:
      - illustrious-anime.json
      - anything-v5.json

  composition:
    priority: 80  # Style takes precedence
    conflicts_with: [photorealistic, realistic]
    max_per_type: 1
```

---

## See Also

- [API_REFERENCE.md](API_REFERENCE.md) - API endpoints for categories
- [INTELLIGENT_GENERATION_ARCHITECTURE.md](INTELLIGENT_GENERATION_ARCHITECTURE.md) - System design
- [USAGE.md](USAGE.md) - Using @tags in prompts

---

**Documentation Policy:** This is an authoritative reference for category authoring. Do NOT create additional category documentation files.
