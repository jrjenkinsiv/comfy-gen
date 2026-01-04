# Dynamic LoRA Injection

This document describes how to use dynamic LoRA injection to add LoRAs at generation time without modifying workflow JSON files.

## Overview

LoRAs (Low-Rank Adaptation) are small model adaptations that can modify generation behavior. Previously, LoRAs had to be manually added to workflow JSON files. With dynamic injection, you can:

- Add LoRAs via CLI arguments
- Chain multiple LoRAs together
- Use predefined LoRA presets
- List available LoRAs

## CLI Arguments

### `--lora NAME:STRENGTH`

Add a LoRA with specified strength. Can be repeated for multiple LoRAs.

**Format:** `--lora "filename.safetensors:strength"`

**Example:**
```bash
python3 generate.py \
  --workflow workflows/flux-dev.json \
  --prompt "a beautiful landscape" \
  --lora "style_lora.safetensors:0.8"
```

### `--lora-preset PRESET_NAME`

Use a predefined LoRA preset from `lora_catalog.yaml`.

**Example:**
```bash
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "person walking" \
  --lora-preset "text_to_video"
```

### `--list-loras`

List all available LoRAs and presets, then exit.

**Example:**
```bash
python3 generate.py --list-loras
```

## Usage Examples

### Single LoRA

Add one LoRA with custom strength:

```bash
python3 generate.py \
  --workflow workflows/flux-dev.json \
  --prompt "cyberpunk cityscape, neon lights, rain" \
  --lora "cyberpunk_style.safetensors:0.7" \
  --output cyberpunk.png
```

### Multiple LoRAs (Chaining)

Chain multiple LoRAs together. They are applied in the order specified:

```bash
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "dancer performing, dynamic movement" \
  --lora "BoobPhysics_WAN_v6.safetensors:0.7" \
  --lora "BounceHighWan2_2.safetensors:0.6" \
  --output dancer.mp4
```

**Chain Order:**
```
Model → LoRA 1 → LoRA 2 → ... → Sampler
```

### LoRA Presets

Use predefined combinations from `lora_catalog.yaml`:

```bash
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "action scene with physics" \
  --lora-preset "text_to_video" \
  --output action.mp4
```

### Combining Manual and Preset

You can combine `--lora-preset` with additional `--lora` arguments:

```bash
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "dynamic scene" \
  --lora-preset "text_to_video" \
  --lora "custom_style.safetensors:0.5" \
  --output custom.mp4
```

**Order:** Preset LoRAs are applied first, then manual `--lora` arguments.

## LoRA Strength Guidelines

| Strength | Effect | Use Case |
|----------|--------|----------|
| 0.3-0.5 | Subtle | Minor style adjustments |
| 0.6-0.8 | Moderate | Typical style/physics LoRAs |
| 0.9-1.0 | Strong | Acceleration LoRAs, major changes |
| 1.0+ | Maximum | Some LoRAs work best at 1.0 or higher |

**Note:** Acceleration LoRAs (like 4-step LoRAs) typically require strength of exactly 1.0.

## LoRA Presets

Presets are defined in `lora_catalog.yaml` under `model_suggestions`. Each preset includes:

- Default LoRAs with recommended strengths
- Compatible models
- Use case descriptions

**Example preset definition:**
```yaml
model_suggestions:
  text_to_video:
    model: "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
    workflow: "workflows/wan22-t2v.json"
    default_loras:
      - "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors"
    keywords: ["video", "animation", "motion"]
```

## Validation

LoRAs are validated before injection:

1. **Existence Check:** Verify LoRA exists on server
2. **Server Query:** Get available LoRAs from ComfyUI API
3. **Error Reporting:** Show available alternatives if LoRA not found

**Example error:**
```
[ERROR] LoRA not found: missing_lora.safetensors
[ERROR] Available LoRAs: style_lora.safetensors, physics_lora.safetensors, ...
```

## Technical Details

### How It Works

1. **Workflow Loading:** Load base workflow JSON
2. **LoRA Injection:** Insert LoraLoader nodes dynamically
3. **Connection Rewiring:** Update connections to chain through LoRAs
4. **Generation:** Send modified workflow to ComfyUI

### Workflow Modification

**Before:**
```
CheckpointLoader → KSampler
```

**After (single LoRA):**
```
CheckpointLoader → LoraLoader → KSampler
```

**After (multiple LoRAs):**
```
CheckpointLoader → LoraLoader1 → LoraLoader2 → KSampler
```

### Node Structure

Generated LoRA nodes have this structure:

```json
{
  "class_type": "LoraLoader",
  "inputs": {
    "model": ["1", 0],
    "clip": ["1", 1],
    "lora_name": "lora_file.safetensors",
    "strength_model": 0.8,
    "strength_clip": 0.8
  },
  "_meta": {
    "title": "LoRA: lora_file.safetensors"
  }
}
```

## Compatibility

### Supported Workflows

- ✅ SD 1.5 workflows (CheckpointLoaderSimple)
- ✅ Wan 2.2 workflows (UNETLoader + DualCLIPLoader)
- ✅ SDXL workflows (CheckpointLoaderSimple)
- ✅ Workflows with existing LoRAs (chains automatically)

### Limitations

- LoRAs must exist on the ComfyUI server
- LoRA filenames must be exact (case-sensitive)
- Some LoRAs only work with specific models (see catalog)

## Troubleshooting

### LoRA Not Found

```
[ERROR] LoRA not found: my_lora.safetensors
```

**Solutions:**
1. Check filename spelling and case
2. Run `--list-loras` to see available LoRAs
3. Ensure LoRA is in `C:\Users\jrjen\comfy\models\loras\` on moira

### Server Connection Error

```
[ERROR] ComfyUI server is not available
```

**Solutions:**
1. Verify ComfyUI is running: `ssh moira "tasklist | findstr python"`
2. Start ComfyUI: `python3 scripts/start_comfyui.py`
3. Check network connectivity to 192.168.1.215:8188

### Invalid Strength Value

```
[ERROR] Invalid LoRA strength: abc
```

**Solution:** Strength must be a number (e.g., 0.8, 1.0)

### Preset Not Found

```
[ERROR] LoRA preset not found: my_preset
```

**Solution:** Run `--list-loras` to see available presets, or check `lora_catalog.yaml`

## Best Practices

1. **Start with recommended strengths** from `lora_catalog.yaml`
2. **Use acceleration LoRAs** for faster generation (4-step LoRAs)
3. **Chain physics LoRAs** with acceleration LoRAs for best results
4. **Test single LoRAs** before combining multiple
5. **Use presets** for proven combinations

## Examples

See `examples/lora_injection.py` for complete working examples.

## See Also

- [Agent Guide](AGENT_GUIDE.md) - LoRA selection guidance
- [Model Registry](MODEL_REGISTRY.md) - Available models and LoRAs
- [lora_catalog.yaml](../lora_catalog.yaml) - LoRA definitions and presets
