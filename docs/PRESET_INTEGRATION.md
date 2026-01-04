# Preset Integration Guide

This guide explains how presets and configuration work in ComfyGen for both CLI and MCP server.

## Overview

ComfyGen now uses a unified configuration system that loads settings from `presets.yaml` and `lora_catalog.yaml`. This ensures consistent behavior between the CLI (`generate.py`) and the MCP server.

## Configuration Files

### `presets.yaml`

Contains:
- **default_negative_prompt**: Applied automatically when user doesn't provide one
- **presets**: Named parameter sets (draft, balanced, high-quality, fast, ultra)
- **validation**: Default validation settings
- **negative_prompts**: Subject-specific negative prompt suggestions
- **positive_emphasis**: Positive prompt helpers for single subject emphasis

### `lora_catalog.yaml`

Contains:
- **loras**: Metadata for all available LoRAs
- **model_suggestions**: Predefined scenarios for auto-selection
- **keyword_mappings**: Keywords to tag mappings for intelligent matching

## Using Presets

### CLI Usage

```bash
# Use a preset
python generate.py --workflow workflows/flux-dev.json \
    --prompt "sunset over mountains" \
    --preset draft

# Override preset values
python generate.py --workflow workflows/flux-dev.json \
    --prompt "sunset over mountains" \
    --preset high-quality \
    --steps 30  # Override the preset's 50 steps

# Use LoRA preset
python generate.py --workflow workflows/flux-dev.json \
    --prompt "sunset over mountains" \
    --lora-preset simple_image

# Default negative prompt is applied automatically
python generate.py --workflow workflows/flux-dev.json \
    --prompt "sunset over mountains"
# No --negative-prompt needed, uses default from config
```

### MCP Server Usage

```python
# Use a preset
await generate_image(
    prompt="sunset over mountains",
    preset="draft"
)

# Override preset values
await generate_image(
    prompt="sunset over mountains",
    preset="high-quality",
    steps=30  # Override the preset's 50 steps
)

# Use LoRA preset
await generate_image(
    prompt="sunset over mountains",
    lora_preset="text_to_video"
)

# Default negative prompt is applied automatically
await generate_image(
    prompt="sunset over mountains"
    # negative_prompt="" or omitted → uses default from config
)
```

## Available Presets

### Generation Presets

| Preset | Steps | CFG | Sampler | Use Case |
|--------|-------|-----|---------|----------|
| `draft` | 10 | 5.0 | euler | Fast drafts, no validation |
| `balanced` | 20 | 7.0 | euler_ancestral | Good quality/speed tradeoff |
| `high-quality` | 50 | 7.5 | dpmpp_2m_sde | High quality, auto-retry enabled |
| `fast` | 15 | 7.0 | dpmpp_2m | Fast with good quality |
| `ultra` | 100 | 8.0 | dpmpp_2m_sde | Maximum quality, very slow |

### LoRA Presets

| Preset | Model | LoRAs | Use Case |
|--------|-------|-------|----------|
| `text_to_video` | wan2.2_t2v_high_noise | 4-step acceleration | Video generation from text |
| `image_to_video` | wan2.2_i2v_high_noise | 4-step acceleration | Animate existing images |
| `simple_image` | SD 1.5 | None | Basic image generation |
| `battleship_ship_icon` | SD 1.5 | None | Game asset: ship icons |

## Parameter Override Priority

When using presets, parameter values are resolved in this order (highest to lowest priority):

1. **Explicitly provided parameters** (e.g., `steps=30`)
2. **Preset values** (e.g., from `preset="draft"`)
3. **Default values** (hardcoded in the function)

### Example

```python
# Using draft preset with override
await generate_image(
    prompt="sunset",
    preset="draft",    # steps=10, cfg=5.0, validate=False
    steps=25,          # Override steps to 25
    # cfg not specified → uses preset value 5.0
    # validate not specified → uses preset value False
)

# Result:
# - steps: 25 (explicit override)
# - cfg: 5.0 (from preset)
# - validate: False (from preset)
# - sampler: euler (from preset)
# - scheduler: normal (from preset)
```

## Default Negative Prompt

The default negative prompt from `presets.yaml` is automatically applied when:
- User provides `negative_prompt=""` (empty string)
- User omits `negative_prompt` parameter in MCP

Current default:
```
bad quality, blurry, low resolution, watermark, text, signature, 
deformed, ugly, extra limbs, mutated, disfigured, poorly drawn, 
bad anatomy, jpeg artifacts
```

To bypass the default and use no negative prompt:
- CLI: Provide `--negative-prompt " "` (space)
- MCP: Provide `negative_prompt=" "` (space)

## Validation Settings

Validation settings are also loaded from `presets.yaml`:

```yaml
validation:
  enabled: true
  auto_retry: true
  retry_limit: 3
  positive_threshold: 0.25
```

These can be overridden by:
- CLI: `--validate`, `--no-validate`, `--auto-retry`, etc.
- MCP: `validate=True`, `auto_retry=False`, etc.
- Presets: Individual presets can override these (e.g., `draft` sets `validate: false`)

## Implementation Details

### Shared Config Loader

Both CLI and MCP use the same config loader from `comfygen/config.py`:

```python
from comfygen.config import (
    load_presets_config,  # Load presets.yaml
    load_lora_catalog,    # Load lora_catalog.yaml
    get_preset,           # Get specific preset
    get_lora_preset,      # Get specific LoRA preset
    apply_preset_to_params  # Apply preset to parameters
)
```

### MCP Startup

The MCP server loads configuration on startup:

```python
# In mcp_server.py
from comfygen.config import load_presets_config, load_lora_catalog

_config = load_presets_config()
_lora_catalog = load_lora_catalog()
```

This ensures configuration is loaded once and reused across all requests.

### CLI Usage

The CLI loads configuration on demand:

```python
# In generate.py
from comfygen.config import load_presets_config

config = load_config()  # Uses load_presets_config internally
```

## Testing

Tests are available to verify preset integration:

```bash
# Test config loading
python tests/test_preset_integration.py

# Test MCP server preset usage
python tests/test_mcp_preset_usage.py

# Test MCP server overall
python tests/test_comprehensive_mcp.py

# Demo preset integration
python examples/demo_preset_integration.py
```

## Benefits

1. **Consistency**: CLI and MCP behave identically with same parameters
2. **Convenience**: Default negative prompt applied automatically
3. **Flexibility**: Presets provide quick access to common configurations
4. **Override**: All preset values can be overridden explicitly
5. **Maintainability**: Single source of truth for configuration
