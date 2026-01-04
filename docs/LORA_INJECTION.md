# Dynamic LoRA Injection Guide

This guide explains how to use the dynamic LoRA injection feature in ComfyGen.

## Overview

LoRAs (Low-Rank Adaptations) allow you to modify the behavior of base models without changing the models themselves. ComfyGen now supports dynamically adding LoRAs at generation time via CLI arguments, without needing to modify workflow JSON files.

## Basic Usage

### Single LoRA

Add a single LoRA to your generation:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a beautiful sunset over mountains" \
    --lora "style_lora.safetensors:0.8" \
    --output /tmp/sunset.png
```

The format is `--lora FILENAME:STRENGTH` where:
- `FILENAME` is the LoRA filename (must exist in `C:\Users\jrjen\comfy\models\loras\` on moira)
- `STRENGTH` is a float between 0.0 and 1.0+ (optional, defaults to 1.0)

### Multiple LoRAs (Chained)

You can chain multiple LoRAs by repeating the `--lora` argument:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a red sports car on a winding road" \
    --lora "style_lora.safetensors:0.7" \
    --lora "detail_enhancer.safetensors:0.5" \
    --output /tmp/car.png
```

LoRAs are applied in the order specified. The first LoRA receives input from the checkpoint, the second from the first LoRA, and so on.

### List Available LoRAs

To see what LoRAs are available on the server:

```bash
python3 generate.py --list-loras
```

This queries the ComfyUI API and displays all LoRAs found in the models directory.

## LoRA Presets

For common LoRA combinations, you can define presets in `lora_presets.yaml`.

### Using a Preset

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a person walking" \
    --lora-preset video-quality \
    --output /tmp/video.mp4
```

### Defining Presets

Edit `lora_presets.yaml`:

```yaml
presets:
  my-preset:
    - name: "first_lora.safetensors"
      strength: 0.7
    - name: "second_lora.safetensors"
      strength: 0.5
```

### Combining Presets and Individual LoRAs

You can combine presets with additional LoRAs:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "..." \
    --lora-preset fast-generation \
    --lora "extra_lora.safetensors:0.6"
```

Preset LoRAs are applied first, then individual `--lora` arguments.

## LoRA Strength Guidelines

| Strength | Effect | Use Case |
|----------|--------|----------|
| 0.3-0.5 | Subtle | Minor style adjustments |
| 0.6-0.8 | Moderate | Standard use case |
| 0.9-1.0 | Strong | Dominant effect |
| 1.0+ | Very strong | May cause artifacts, use carefully |
| Negative | Inverse | Opposite of LoRA's intended effect |

## Technical Details

### How It Works

When you specify `--lora` arguments:

1. **Parse Arguments**: The CLI parses each `--lora` argument into (name, strength) pairs
2. **Validate**: The system queries ComfyUI to verify the LoRAs exist
3. **Load Workflow**: The base workflow JSON is loaded
4. **Find Checkpoint**: The system finds the `CheckpointLoaderSimple` node
5. **Inject LoRAs**: New `LoraLoader` nodes are inserted between the checkpoint and its consumers
6. **Rewire Connections**: All downstream nodes (KSampler, CLIPTextEncode) are rewired to use the last LoRA's output
7. **Queue**: The modified workflow is sent to ComfyUI

### Node Structure

A single LoRA injection creates this structure:

```
CheckpointLoader (node 1)
    |
    v
LoraLoader (node 8)
    |
    v
KSampler, CLIPTextEncode, etc.
```

Multiple LoRAs create a chain:

```
CheckpointLoader (node 1)
    |
    v
LoraLoader (node 8) - first_lora.safetensors:0.7
    |
    v
LoraLoader (node 9) - second_lora.safetensors:0.5
    |
    v
LoraLoader (node 10) - third_lora.safetensors:0.6
    |
    v
KSampler, CLIPTextEncode, etc.
```

### Compatibility

This feature works with any workflow that has a `CheckpointLoaderSimple` node. It automatically:
- Finds the checkpoint loader
- Identifies what nodes consume the model and CLIP outputs
- Inserts LoRA nodes in between
- Maintains all other workflow connections

## Examples

### Example 1: Video Generation with Acceleration

```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a car driving down a coastal highway" \
    --lora "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors:1.0" \
    --output /tmp/drive.mp4
```

This uses the 4-step acceleration LoRA to speed up video generation.

### Example 2: Enhanced Physics

```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a person jumping" \
    --lora "BoobPhysics_WAN_v6.safetensors:0.7" \
    --lora "BounceHighWan2_2.safetensors:0.6" \
    --output /tmp/jump.mp4
```

### Example 3: Using Presets

```bash
# Fast generation preset
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a sunset over ocean waves" \
    --lora-preset fast-generation \
    --output /tmp/sunset.mp4

# Video quality preset
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a person dancing" \
    --lora-preset video-quality \
    --output /tmp/dance.mp4
```

## Troubleshooting

### LoRA Not Found

```
[ERROR] LoRA not found: my_lora.safetensors
```

**Solution**: Run `--list-loras` to see available LoRAs. Ensure the filename matches exactly (case-sensitive).

### Invalid Strength

```
[WARN] Invalid strength 'abc' for LoRA 'test.safetensors', using 1.0
```

**Solution**: Strength must be a number. Use format `name.safetensors:0.8`.

### No CheckpointLoader Found

```
[ERROR] No CheckpointLoaderSimple node found in workflow
```

**Solution**: The workflow must contain a `CheckpointLoaderSimple` node. This feature doesn't work with workflows that load models differently.

### Server Connection Issues

If LoRA validation fails with connection errors, check that ComfyUI is running:

```bash
curl -s http://192.168.1.215:8188/system_stats
```

## Available LoRA Presets

The default `lora_presets.yaml` includes:

- **video-quality**: Physics and motion enhancements for video
- **fast-generation**: Acceleration LoRAs for 4-step generation
- **physics-enhanced**: Maximum physics simulation

See `lora_presets.yaml` for the full list and edit it to add your own presets.

## References

- Model Registry: `docs/MODEL_REGISTRY.md`
- Agent Guide: `docs/AGENT_GUIDE.md`
- LoRA files location: `C:\Users\jrjen\comfy\models\loras\` (on moira)
