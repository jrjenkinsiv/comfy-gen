# MCP Preset Integration Summary

## Overview

This document summarizes the integration of `presets.yaml` and `lora_catalog.yaml` configuration into the MCP server to ensure CLI and MCP produce identical outputs.

## Changes Made

### 1. New Config Module (`comfygen/config.py`)

Created a centralized configuration loader that:
- Loads `presets.yaml` and `lora_catalog.yaml` from the project root
- Provides methods to access:
  - Default negative prompt
  - Generation presets (draft, balanced, high-quality, fast, ultra)
  - LoRA presets (text_to_video, image_to_video, simple_image)
  - Validation configuration
- Uses singleton pattern to ensure config is loaded only once
- Shared by both CLI and MCP for consistency

### 2. MCP Server Updates (`mcp_server.py`)

Updated all generation tools to use config:

**`generate_image` tool:**
- Added `preset` parameter (optional): Selects generation preset
- Added `lora_preset` parameter (optional): Selects LoRA preset from catalog
- Changed default `negative_prompt` to empty string (uses config default)
- Parameters are now optional (`steps`, `cfg`, `sampler`, `scheduler`) with preset defaults
- Override priority: explicit args > preset > hardcoded defaults

**Other generation tools (`img2img`, `generate_video`, `image_to_video`):**
- Changed default `negative_prompt` to empty string (uses config default)
- Apply default negative prompt from config when user doesn't provide one

### 3. Tests Added

Created comprehensive test suite:

1. **`tests/test_config.py`** - Tests config module functionality
   - Config loading
   - Preset resolution
   - LoRA catalog loading
   - LoRA preset resolution
   - Validation configuration
   - Singleton pattern
   - Error handling

2. **`tests/test_mcp_presets.py`** - Tests MCP server integration
   - Config loaded on startup
   - Tool schema validation
   - Parameter defaults
   - Config accessibility

3. **`tests/test_cli_mcp_consistency.py`** - Tests CLI/MCP consistency
   - Preset parameters match
   - Override logic consistency
   - Config file locations

4. **`tests/verify_cli_mcp_equivalence.py`** - Manual verification script
   - Simulates CLI and MCP parameter resolution
   - Compares configurations for multiple scenarios
   - Verifies identical output

## Usage Examples

### Using Presets

**CLI:**
```bash
python generate.py --workflow workflows/flux-dev.json \
    --prompt "a beautiful sunset" \
    --preset balanced
```

**MCP:**
```python
await generate_image(
    prompt="a beautiful sunset",
    preset="balanced"
)
```

Both produce:
- steps=20
- cfg=7.0
- sampler=euler_ancestral
- scheduler=normal
- negative_prompt from config

### Using LoRA Presets

**CLI:**
```bash
python generate.py --workflow workflows/wan22-t2v.json \
    --prompt "a cat walking" \
    --lora-preset text_to_video
```

**MCP:**
```python
await generate_image(
    prompt="a cat walking",
    lora_preset="text_to_video"
)
```

Both apply:
- `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` with strength 1.0

### Overriding Preset Parameters

**CLI:**
```bash
python generate.py --workflow workflows/flux-dev.json \
    --prompt "a beautiful sunset" \
    --preset balanced \
    --steps 15
```

**MCP:**
```python
await generate_image(
    prompt="a beautiful sunset",
    preset="balanced",
    steps=15
)
```

Both produce:
- steps=15 (override)
- cfg=7.0 (from preset)
- sampler=euler_ancestral (from preset)
- scheduler=normal (from preset)

## Available Presets

### Generation Presets (from `presets.yaml`)

| Preset | Steps | CFG | Sampler | Scheduler | Use Case |
|--------|-------|-----|---------|-----------|----------|
| draft | 10 | 5.0 | euler | normal | Fast previews |
| balanced | 20 | 7.0 | euler_ancestral | normal | Good quality/speed balance |
| high-quality | 50 | 7.5 | dpmpp_2m_sde | karras | High quality output |
| fast | 15 | 7.0 | dpmpp_2m | normal | Fast with good quality |
| ultra | 100 | 8.0 | dpmpp_2m_sde | karras | Maximum quality |

### LoRA Presets (from `lora_catalog.yaml`)

| Preset | Model | Default LoRAs | Use Case |
|--------|-------|---------------|----------|
| text_to_video | Wan 2.2 T2V | 4-step acceleration LoRA | Fast video generation |
| image_to_video | Wan 2.2 I2V | 4-step acceleration LoRA | Fast image animation |
| simple_image | SD 1.5 | None | Basic image generation |

## Verification Results

All tests pass:
- ✅ Config module loads successfully
- ✅ MCP server uses config on startup
- ✅ Preset parameters apply correctly
- ✅ LoRA presets resolve correctly
- ✅ Default negative prompt applied when not specified
- ✅ CLI and MCP produce identical configurations

Run all tests:
```bash
python3 tests/test_config.py
python3 tests/test_mcp_presets.py
python3 tests/test_cli_mcp_consistency.py
python3 tests/verify_cli_mcp_equivalence.py
```

## Impact

### Before
- MCP used hardcoded defaults
- CLI and MCP could produce different outputs with "same" parameters
- Presets only available in CLI
- LoRA presets only available in CLI
- No centralized config management

### After
- MCP loads config from `presets.yaml` and `lora_catalog.yaml`
- CLI and MCP produce identical outputs with same parameters
- Presets available in both CLI and MCP
- LoRA presets available in both CLI and MCP
- Centralized config management via `comfygen/config.py`

## Future Enhancements

Potential improvements:
1. Add preset validation (ensure required keys exist)
2. Support custom preset directories
3. Add config hot-reloading
4. Expand validation configuration options
5. Add more preset categories (style presets, quality presets, etc.)
