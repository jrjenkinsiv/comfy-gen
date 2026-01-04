# LoRA Catalog Documentation

This document describes the LoRA catalog system used for intelligent model and LoRA selection in ComfyGen.

## Overview

The LoRA catalog (`lora_catalog.yaml`) contains semantic descriptions and metadata for all LoRAs installed on moira. This enables agents and the auto-selection system to intelligently choose appropriate LoRAs based on prompt content.

## Catalog Structure

The catalog is divided into three main sections:

### 1. LoRA Definitions

Each LoRA entry contains:

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Exact filename of the LoRA in `models/loras/` |
| `tags` | array | Semantic tags for matching (e.g., "physics", "motion", "acceleration") |
| `compatible_with` | array | List of model filenames this LoRA works with |
| `recommended_strength` | float | Recommended strength value (0.0 to 1.0+) |
| `description` | string | Human-readable description of what the LoRA does |
| `use_cases` | array | List of scenarios where this LoRA is useful |

**Example:**
```yaml
- filename: "BounceHighWan2_2.safetensors"
  tags: ["physics", "motion", "bounce", "wan2.2", "high-noise", "dynamic"]
  compatible_with: ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"]
  recommended_strength: 0.7
  description: "Adds dynamic bounce and motion effects for high noise Wan 2.2 models"
  use_cases: ["dynamic motion", "bounce effects", "energetic movement", "action scenes"]
```

### 2. Model Suggestions

Predefined model and workflow suggestions for common scenarios:

| Scenario | Model | Workflow | Keywords |
|----------|-------|----------|----------|
| `text_to_video` | Wan 2.2 T2V High | wan22-t2v.json | video, animation, motion |
| `image_to_video` | Wan 2.2 I2V High | wan22-i2v.json | animate, bring to life |
| `simple_image` | SD 1.5 | flux-dev.json | image, photo, picture |

**Example:**
```yaml
text_to_video:
  model: "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
  workflow: "workflows/wan22-t2v.json"
  default_loras:
    - "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors"
  keywords: ["video", "animation", "motion", "movement", "scene", "action"]
```

### 3. Keyword Mappings

Maps prompt keywords to LoRA tags with boost scores for intelligent matching:

```yaml
keyword_mappings:
  motion:
    tags: ["motion", "dynamic"]
    boost_score: 1.5
```

When a prompt contains "motion", LoRAs with "motion" or "dynamic" tags get a 1.5x boost in their selection score.

## Selection Algorithm

The `scripts/select_model.py` script uses this catalog to suggest models and LoRAs:

1. **Analyze prompt** - Extract keywords and detect content type
2. **Select model/workflow** - Match to text-to-video, image-to-video, or simple image
3. **Query available models** - Verify models exist via ComfyUI API
4. **Score LoRAs** - Calculate scores based on tag matches and keyword boosts
5. **Select top LoRAs** - Choose highest-scoring compatible LoRAs
6. **Provide reasoning** - Explain why each selection was made

## Usage

### Manual Selection
```bash
# Get suggestions for a prompt
python3 scripts/select_model.py "a car driving fast with motion blur"

# Output:
# Model: wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors
# Workflow: workflows/wan22-t2v.json
# LoRAs:
#   - wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors (strength: 1.0)
#     Reason: Default acceleration LoRA for fast generation
#   - BounceHighWan2_2.safetensors (strength: 0.7)
#     Reason: Matched keywords: motion (score: 1.5)
```

### Auto-Selection in generate.py
```bash
# Use --auto-select flag for automatic model/LoRA selection
python3 generate.py --auto-select --prompt "dynamic action scene with motion blur" --output /tmp/action.mp4

# The system will:
# 1. Analyze the prompt
# 2. Select appropriate model/workflow
# 3. Choose relevant LoRAs
# 4. Modify the workflow
# 5. Generate the output
```

## LoRA Categories

### Acceleration LoRAs
- **Purpose:** Reduce generation steps from 30+ to 4 steps
- **Strength:** Always use 1.0
- **Compatibility:** Must match exact model variant (high/low noise, t2v/i2v)
- **Tags:** acceleration, speed, 4-step

### Physics/Motion LoRAs
- **Purpose:** Enhance realism and motion quality
- **Strength:** Start at 0.7, adjust based on results
- **Compatibility:** Work with multiple Wan 2.2 variants
- **Tags:** physics, motion, bounce, dynamic

### Enhancement LoRAs
- **Purpose:** Modify or enhance specific aspects
- **Strength:** 0.6-0.8 typically
- **Compatibility:** Model-specific
- **Tags:** body, character, enhancement

## Adding New LoRAs

To add a new LoRA to the catalog:

1. **Download LoRA** to `C:\Users\jrjen\comfy\models\loras\` on moira
2. **Test compatibility** with target models
3. **Add entry to catalog:**
   ```yaml
   - filename: "new_lora.safetensors"
     tags: ["relevant", "semantic", "tags"]
     compatible_with: ["model_name.safetensors"]
     recommended_strength: 0.7
     description: "What this LoRA does"
     use_cases: ["when to use it"]
   ```
4. **Update MODEL_REGISTRY.md** with the new LoRA
5. **Test selection** with `scripts/select_model.py`

## Best Practices

### Tagging Guidelines
- Use **semantic tags** that describe what the LoRA does, not just its name
- Include **compatibility tags** (e.g., "wan2.2", "high-noise")
- Add **effect tags** (e.g., "motion", "physics", "enhancement")
- Use **use-case tags** (e.g., "acceleration", "character")

### Strength Recommendations
- **1.0:** Acceleration LoRAs, must-use LoRAs
- **0.7-0.9:** Primary effect LoRAs
- **0.5-0.7:** Secondary/subtle effect LoRAs
- **0.3-0.5:** Minimal influence LoRAs

### Compatibility
- Always test LoRA with target model before adding to catalog
- List ALL compatible models, not just the primary one
- Note any special requirements (e.g., specific noise levels)

## Troubleshooting

### LoRA Not Being Selected
1. Check tags match prompt keywords
2. Verify compatibility with selected model
3. Check keyword_mappings for boost opportunities
4. Ensure LoRA exists in API response

### Wrong Model Selected
1. Verify prompt contains appropriate keywords
2. Check model_suggestions section
3. Consider adding new keywords to model suggestions

### LoRA Strength Issues
- Too strong: Reduce recommended_strength in catalog
- Too weak: Increase recommended_strength in catalog
- Inconsistent: Add notes to description about strength sensitivity

## See Also

- [MODEL_REGISTRY.md](MODEL_REGISTRY.md) - Complete model inventory
- [AGENT_GUIDE.md](AGENT_GUIDE.md) - Agent usage guide
- `scripts/select_model.py` - Selection script implementation
