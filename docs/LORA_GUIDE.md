# LoRA Selection Guide

## CRITICAL: Video vs Image LoRAs

**NEVER use video LoRAs for image generation.** This causes:
- Distorted anatomy (weird breasts, floating body parts)
- Merged/duplicated features
- Poor quality output

### How to Tell the Difference

**File Size is the Key:**

| Type | Size Range | Example |
|------|------------|---------|
| **SD 1.5 Image LoRAs** | 10-170 MB | `airoticart_penis.safetensors` (151 MB) |
| **Wan 2.2 Video LoRAs** | 300+ MB | `erect_penis_epoch_80.safetensors` (307 MB) |

### Common Mistake: Wrong Penis LoRA

**WRONG (Video LoRA):**
```bash
--lora "erect_penis_epoch_80.safetensors:0.6"  # 307 MB - WAN 2.2 VIDEO LORA!
--lora "deepthroat_epoch_80.safetensors:0.6"   # 307 MB - WAN 2.2 VIDEO LORA!
--lora "dicks_epoch_100.safetensors:0.6"       # 307 MB - WAN 2.2 VIDEO LORA!
```

**CORRECT (Image LoRA):**
```bash
--lora "airoticart_penis.safetensors:0.85"     # 151 MB - SD 1.5 IMAGE LORA
```

### Validated SD 1.5 Image LoRAs (by size)

| LoRA | Size | Use Case | Trigger Words |
|------|------|----------|---------------|
| `airoticart_penis.safetensors` | 151 MB | Male anatomy for photos | `penerec` (erect), `penflac` (flaccid) |
| `polyhedron_skin.safetensors` | 151 MB | Realistic skin texture | `detailed skin` |
| `realora_skin.safetensors` | 151 MB | Subtle skin enhancement | (none needed) |
| `more_details.safetensors` | 10 MB | Detail enhancement | (none needed) |
| `add_detail.safetensors` | 38 MB | Detail tweaker | (none needed) |

### Video LoRAs (DO NOT use for images)

These are ~307 MB and designed for Wan 2.2 video models:

- `erect_penis_epoch_80.safetensors` - Video LoRA
- `deepthroat_epoch_80.safetensors` - Video LoRA
- `dicks_epoch_100.safetensors` - Video LoRA
- `flaccid_penis_epoch_100.safetensors` - Video LoRA
- `big_breasts_v2_epoch_30.safetensors` - Video LoRA
- `BoobPhysics_WAN_v6.safetensors` - Video LoRA
- `BounceHighWan2_2.safetensors` - Video LoRA
- All files with `wan`, `WAN`, `i2v`, `t2v` in name - Video LoRAs

---

## Optimal Settings for NSFW Image Generation

### Steps and CFG

| Quality Level | Steps | CFG | Use Case |
|--------------|-------|-----|----------|
| Draft | 30-40 | 7.0 | Quick testing |
| Standard | 50-60 | 8.0-9.0 | Normal batch runs |
| High Quality | 70-80 | 8.5-9.5 | Final outputs |

**Higher steps = better detail but slower.** For NSFW content with complex anatomy:
- Minimum 50 steps recommended
- 60-70 steps for consistent results
- 80+ steps for maximum quality

**CFG (Classifier Free Guidance):**
- 7.0-8.0: More creative, can drift from prompt
- 8.5-9.5: Stricter prompt adherence (recommended for NSFW)
- 10.0+: Very strict, can cause artifacts

### Recommended Settings for Explicit Content

```bash
python3 generate.py \
    --workflow workflows/majicmix-realistic.json \
    --prompt "your explicit prompt here" \
    --negative-prompt "bad anatomy, extra limbs, duplicate, etc" \
    --steps 60 \
    --cfg 9.0 \
    --width 768 \
    --height 1024 \
    --lora "airoticart_penis.safetensors:0.85" \
    --lora "polyhedron_skin.safetensors:0.5" \
    --output /tmp/output.png
```

### LoRA Stacking Best Practices

1. **Anatomy LoRA first** (strength 0.8-0.9)
2. **Skin/detail LoRAs second** (strength 0.4-0.6)
3. **Total combined strength** should not exceed ~1.5

Example:
```bash
--lora "airoticart_penis.safetensors:0.85" \
--lora "polyhedron_skin.safetensors:0.5" \
--lora "add_detail.safetensors:0.3"
```

---

## POV Prompting for Multi-Body Scenes

SD 1.5 models struggle with two distinct human bodies. Use POV (point of view) prompts:

### POV Technique

Instead of:
```
"woman sucking man's cock, man standing"  # BAD - two bodies
```

Use:
```
"(POV shot:1.4), (first person perspective:1.3), 
woman sucking cock, cock entering from bottom of frame,
viewer's cock, looking up at camera"  # GOOD - one visible body
```

### Key POV Markers

- `(POV shot:1.4)` - Main perspective marker
- `(first person perspective:1.3)` - Reinforcement
- `cock entering from bottom of frame` - Spatial positioning
- `viewer's cock` - Establishes ownership
- Negative: `man's body visible, standing man, full male body`

---

## Trigger Words Reference

### airoticart_penis.safetensors

| State | Trigger Word | Usage |
|-------|--------------|-------|
| Erect | `penerec` | Add to positive prompt |
| Flaccid | `penflac` | Add to positive prompt |

**Best practice:** Add opposite trigger to negative prompt.

Example for erect penis:
```
--prompt "... penerec, erect penis ..."
--negative-prompt "... penflac, soft penis, flaccid ..."
```

### polyhedron_skin.safetensors

Trigger words: `detailed skin`, `skin blemish`, `skin pores`

### PixelArtRedmond15V (Pixel Art)

Trigger word: `pixarfk` or `pixel art style`

### GothicPixelArtV1.1 (Gothic Pixel)

Trigger word: `gothic pixel art`
