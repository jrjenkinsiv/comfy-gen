# LoRA Selection Guide

**Last verified:** 2026-01-05

## CRITICAL: Video vs Image LoRAs

**NEVER use video LoRAs for image generation.** This causes:
- Distorted anatomy (weird breasts, floating body parts)
- Merged/duplicated features
- Poor quality output

### How to Tell the Difference

**Use CivitAI `baseModel` field - NOT file size!**

File size can correlate with model type, but the **authoritative source** is the
`baseModel` field from CivitAI API. Use `scripts/civitai_audit.py` to verify.

**Hash Lookup Method (Recommended):**
```bash
# 1. Get SHA256 hash of the LoRA file
ssh moira "powershell -Command \"(Get-FileHash -Algorithm SHA256 '<path>').Hash\""

# 2. Look up on CivitAI API
curl "https://civitai.com/api/v1/model-versions/by-hash/<HASH>"
# Response includes: baseModel, trainedWords, modelId
```

**Base Model Categories:**
| Base Model | Use For | Example |
|------------|---------|---------|
| `SD 1.5` | Image generation (majicmix, realistic vision) | `airoticart_penis.safetensors` |
| `SDXL 1.0` | High-res image generation | Various SDXL LoRAs |
| `Pony` | Stylized image generation | Various Pony LoRAs |
| `Wan Video 14B t2v/i2v` | Video generation ONLY | `erect_penis_epoch_80.safetensors` |
| `Flux` | Flux image generation | `nsfw_master_flux.safetensors` |

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

### Verified SD 1.5 Image LoRAs (CivitAI Confirmed)

| LoRA | CivitAI ID | Base Model | Trigger Words |
|------|------------|------------|---------------|
| `airoticart_penis.safetensors` | 15040 | SD 1.5 | `penerec` (erect), `penflac` (flaccid) |
| `polyhedron_skin.safetensors` | 109043 | SD 1.5 | `detailed skin`, `skin blemish` |
| `realora_skin.safetensors` | 137258 | SD 1.5 | (none needed) |
| `more_details.safetensors` | 82098 | SD 1.5 | (none needed) |
| `add_detail.safetensors` | 58390 | SD 1.5 | (none needed) |

### Verified Wan 2.2 Video LoRAs (DO NOT use for images)

| LoRA | Base Model | Trigger Words |
|------|------------|---------------|
| `erect_penis_epoch_80.safetensors` | Wan Video 14B t2v | `penis` |
| `deepthroat_epoch_80.safetensors` | Wan Video 14B t2v | `blowjob`, `deepthroat` |
| `dicks_epoch_100.safetensors` | Wan Video 14B t2v | (unknown) |
| `flaccid_penis_epoch_100.safetensors` | Wan Video 14B t2v | (unknown) |
| `big_breasts_v2_epoch_30.safetensors` | Wan Video 14B t2v | `big breasts` |
| `BetterTitfuck_v4_July2025.safetensors` | Wan Video 14B t2v | `titfuck` |
| `doggyPOV_v1_1.safetensors` | Wan Video 14B i2v | `POVdog` |
| All files with `wan`, `WAN`, `i2v`, `t2v` in name | Various Wan models | Check trigger |

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

---

**Documentation Policy:** This is an authoritative reference document. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only.
