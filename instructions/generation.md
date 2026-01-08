# ComfyGen Generation Guide

**Last updated:** 2026-01-08

This is the authoritative reference for image/video generation with comfy-gen. **Consult this guide before generating.**

---

## Quick Start

```bash
# Basic image generation
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a golden retriever on a beach, sunset lighting, photorealistic" \
    --steps 25 --cfg 3.5

# With LoRAs
python3 generate.py --workflow workflows/pornmaster-pony-stacked-realism.json \
    --prompt "beautiful woman, photorealistic portrait" \
    --lora "add_detail:0.4" --lora "more_details:0.3" \
    --steps 70 --cfg 9.0

# Video generation
python3 generate.py --workflow workflows/wan22-t2v.json \
    --prompt "golden retriever running on beach, slow motion" \
    --length 81 --fps 16
```

---

## Table of Contents

1. [Workflow Selection](#workflow-selection)
2. [Parameter Reference](#parameter-reference)
3. [LoRA System](#lora-system)
4. [Prompt Strategies](#prompt-strategies)
5. [Validation & Quality](#validation--quality)
6. [Presets](#presets)
7. [Video Generation](#video-generation)
8. [Image-to-Image](#image-to-image)
9. [MLflow Logging](#mlflow-logging)
10. [Output Handling](#output-handling)
11. [Common Patterns](#common-patterns)

---

## Workflow Selection

### Image Workflows

| Workflow | Base Model | Best For | Default Steps/CFG |
|----------|------------|----------|-------------------|
| `flux-dev.json` | Flux Dev FP8 | **General quality**, photorealism, SFW | 25 / 3.5 |
| `sd15-basic.json` | SD 1.5 | Fast general-purpose | 20 / 7.0 |
| `sd15-hires.json` | SD 1.5 | Higher resolution SD 1.5 | 30 / 7.5 |
| `pornmaster-pony-stacked-realism.json` | Pony/SDXL | **NSFW realism** with multiple LoRAs | 70 / 9.0 |
| `pornmaster-pony-lora.json` | Pony/SDXL | NSFW with single LoRA | 50 / 8.0 |
| `majicmix-realistic.json` | SD 1.5 | Realistic portraits | 30 / 7.5 |
| `realistic-vision.json` | SD 1.5 | General realistic | 30 / 7.0 |
| `illustrious-anime.json` | Illustrious | Anime style | 28 / 7.0 |

### Video Workflows

| Workflow | Model | Best For | Default Length |
|----------|-------|----------|----------------|
| `wan22-t2v.json` | Wan 2.2 T2V 14B | **Text-to-video**, general | 81 frames (~5s) |
| `wan22-t2v-low.json` | Wan 2.2 T2V 14B | Faster T2V (lower quality) | 81 frames |
| `wan22-i2v.json` | Wan 2.2 I2V 14B | **Image-to-video**, animation | 81 frames |
| `wan22-i2v-low.json` | Wan 2.2 I2V 14B | Faster I2V | 81 frames |

### Specialty Workflows

| Workflow | Purpose |
|----------|---------|
| `transparent-icon.json` | Icons with transparent background (requires `--transparent`) |
| `upscale-4x.json` | 4x upscaling existing images |
| `sd15-img2img.json` | SD 1.5 image-to-image |
| `pony-img2img.json` | Pony/SDXL image-to-image |

### Decision Tree

```
What are you generating?
├── SFW / General quality → flux-dev.json
├── NSFW realistic → pornmaster-pony-stacked-realism.json
├── NSFW with specific LoRAs → pornmaster-pony-lora.json
├── Anime style → illustrious-anime.json
├── Video from text → wan22-t2v.json
├── Video from image → wan22-i2v.json (with --input-image)
├── Icons/assets → transparent-icon.json (with --transparent)
└── Upscaling → upscale-4x.json (with --input-image)
```

---

## Parameter Reference

### Core Parameters

| Parameter | Flag | Default | Range | Notes |
|-----------|------|---------|-------|-------|
| Steps | `--steps` | 20 | 1-150 | More = better quality, slower. Flux: 20-30, Pony: 50-70 |
| CFG | `--cfg` | 7.0 | 1.0-20.0 | Higher = stricter prompt adherence. Flux: 3-4, Pony: 8-10 |
| Seed | `--seed` | random | -1 to 2^32 | -1 = random. Use fixed seed for reproducibility |
| Width | `--width` | varies | divisible by 8 | Common: 512, 768, 1024, 1280 |
| Height | `--height` | varies | divisible by 8 | Common: 512, 768, 1024, 1280 |
| Sampler | `--sampler` | euler | see list | euler, dpmpp_2m, dpmpp_2m_sde, etc. |
| Scheduler | `--scheduler` | normal | see list | normal, karras, exponential |

### Recommended Settings by Workflow

| Workflow Type | Steps | CFG | Resolution |
|---------------|-------|-----|------------|
| Flux | 20-30 | 3.0-4.0 | 1024x1024 or 1280x768 |
| Pony NSFW | 50-70 | 8.5-9.5 | 768x1280 (portrait) |
| SD 1.5 | 25-35 | 7.0-8.0 | 512x768 |
| Wan Video | 25-40 | 5.0-7.0 | 848x480 or 1280x720 |

### Video Parameters

| Parameter | Flag | Default | Notes |
|-----------|------|---------|-------|
| Length | `--length` / `--frames` | 81 | Frames. 81 = ~5s at 16fps |
| FPS | `--fps` | 16 | Output framerate |
| Resolution | `--video-resolution` | 848x480 | WxH format |

---

## LoRA System

### Adding LoRAs

```bash
# Single LoRA
--lora "add_detail:0.4"

# Multiple LoRAs (repeat flag)
--lora "add_detail:0.4" --lora "more_details:0.3" --lora "Pale_Skin_SDXL:0.4"

# LoRA preset (from lora_catalog.yaml)
--lora-preset pony_realism
```

### Common LoRAs by Category

**Realism Enhancement (Pony/SDXL):**
| LoRA | Strength | Purpose |
|------|----------|---------|
| `add_detail` | 0.3-0.5 | General detail enhancement |
| `more_details` | 0.2-0.4 | Additional micro-details |
| `Pale_Skin_SDXL` | 0.3-0.5 | Realistic pale skin tones |
| `polyhedron_skin` | 0.3-0.5 | Skin texture (SD 1.5) |
| `realora_skin` | 0.3-0.5 | Natural skin (SD 1.5) |

**NSFW (Pony/SDXL):**
| LoRA | Strength | Trigger Words |
|------|----------|---------------|
| `realcumv6.55` | 0.5-0.7 | cumshot, facial |
| `airoticart_penis` | 0.4-0.6 | penerec (erect), penflac (flaccid) |
| `zy_AmateurStyle_v2` | 0.4-0.6 | amateur style |

**Video (Wan 2.2):**
| LoRA | Type | Purpose |
|------|------|---------|
| `wan2.2_t2v_*_lora` | T2V | Acceleration (4-8 steps) |
| `wan2.2_i2v_*_lora` | I2V | Acceleration |
| `BoobPhysics_WAN_v6` | Both | Physics simulation |
| `BounceHighWan2_2` | Both | Movement effects |

**Flux:**
| LoRA | Strength | Purpose |
|------|----------|---------|
| `Hyper-FLUX.1-dev-8steps-lora` | 0.125 | 8-step acceleration |
| `nsfw_master_flux` | 0.6-0.8 | NSFW capability |

### Listing Available LoRAs

```bash
python3 generate.py --list-loras
```

### CRITICAL: LoRA Compatibility

**NEVER mix LoRAs across base models!**

| Base Model | Compatible LoRAs |
|------------|------------------|
| SD 1.5 | airoticart_penis, polyhedron_skin, realora_skin |
| SDXL/Pony | add_detail, more_details, Pale_Skin_SDXL, realcumv6.55 |
| Flux | Hyper-FLUX, nsfw_master_flux |
| Wan 2.2 | All `wan*` prefixed LoRAs |

See `lora_catalog.yaml` for complete compatibility info.

---

## Prompt Strategies

### Flux (Verbose Detailed)

Flux responds well to **long, descriptive prompts** (100-200 tokens):

```
A golden retriever sitting on a sandy beach at sunset. The dog has a 
lustrous reddish-gold coat catching the warm evening light. Gentle waves 
lap at the shore in the background. Professional wildlife photography, 
sharp focus on the dog's face, shallow depth of field, golden hour 
lighting creating rim light around the fur. Canon EOS R5, 85mm lens, 
f/2.8 aperture.
```

### Pony/SDXL NSFW (Short + Tags + LoRAs)

Use **short, focused prompts** with weighted tags:

```
score_9, score_8_up, (beautiful redhead woman:1.4), (large natural breasts:1.3),
(photorealistic:1.2), bedroom, soft natural lighting, looking at viewer
```

Key syntax:
- `score_9, score_8_up` - Quality tags (Pony-specific)
- `(keyword:1.3)` - Weight boost (1.0-1.5 range)
- Colloquial terms work better (cock not penis, tits not breasts)

### Negative Prompts

Always include negative prompts for quality:

**General:**
```
bad quality, blurry, low resolution, watermark, text, deformed, ugly, duplicate
```

**NSFW Pony:**
```
score_6, score_5, score_4, bad anatomy, extra fingers, extra limbs, 
deformed hands, bad hands, fused fingers, poorly drawn face, mutation
```

**Flux:**
```
blurry, low quality, distorted, deformed, ugly, bad anatomy, 
watermark, text, signature
```

---

## Validation & Quality

### CLIP Validation

```bash
# Enable validation (returns score 0-1)
--validate

# Set minimum threshold
--positive-threshold 0.65

# Auto-retry if below threshold
--auto-retry --retry-limit 3
```

Score interpretation:
| Score | Quality |
|-------|---------|
| 0.70+ | Excellent |
| 0.65-0.70 | Good |
| 0.55-0.65 | Acceptable |
| <0.55 | Poor - retry |

### Additional Validation

```bash
--validate-person-count  # YOLO person detection
--validate-pose          # MediaPipe skeleton coherence
--validate-content       # BLIP-2 content verification
```

### Quality Scoring

```bash
--quality-score          # Multi-dimensional quality analysis
--quality-threshold 7.0  # Minimum score (0-10)
--max-attempts 3         # Retry attempts
--retry-strategy progressive  # progressive|seed_search|prompt_enhance
```

---

## Presets

### Generation Presets

```bash
--preset draft          # Fast, lower quality (steps: 15, cfg: 5)
--preset balanced       # Default balance (steps: 25, cfg: 7)
--preset high-quality   # Slow, best quality (steps: 50, cfg: 8)
```

### Prompt Presets

```bash
# List available presets
python3 generate.py --list-presets

# Use a preset
--prompt-preset nude_woman_garden
```

Presets are defined in `prompt_catalog.yaml`.

### LoRA Presets

```bash
# Use a LoRA preset (loads multiple LoRAs with tuned strengths)
--lora-preset pony_realism
```

Presets are defined in `lora_catalog.yaml`.

---

## Video Generation

### Text-to-Video (T2V)

```bash
python3 generate.py --workflow workflows/wan22-t2v.json \
    --prompt "golden retriever running on beach, slow motion, dynamic camera" \
    --length 81 --fps 16 --video-resolution 848x480 \
    --steps 30 --cfg 6.0
```

### Image-to-Video (I2V)

```bash
python3 generate.py --workflow workflows/wan22-i2v.json \
    --input-image /path/to/start_frame.png \
    --prompt "camera slowly zooms in, subtle movement" \
    --length 81 --fps 16
```

### Video LoRAs

```bash
# Physics simulation
--lora "BoobPhysics_WAN_v6:0.7"

# Acceleration (4-step)
--lora "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise:0.8"
```

---

## Image-to-Image

### Basic Img2Img

```bash
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image /path/to/source.png \
    --prompt "oil painting style" \
    --denoise 0.7  # 0.0=no change, 1.0=full generation
```

### Resize Options

```bash
--resize 768x1024        # Resize to specific dimensions
--crop center            # center, cover, contain
```

### Upscaling

```bash
python3 generate.py --workflow workflows/upscale-4x.json \
    --input-image /path/to/small.png \
    --output /tmp/upscaled.png
```

---

## MLflow Logging

### Auto-Log to MLflow

```bash
# Log with default experiment (comfy-gen-nsfw)
--mlflow-log

# Log to specific experiment
--mlflow-log --mlflow-experiment "comfy-gen-flux-sfw"
```

### What Gets Logged

- All generation parameters (steps, cfg, seed, resolution, sampler, scheduler)
- Workflow file used
- Full prompt and negative prompt
- LoRAs with strengths
- Validation scores
- Image URL (MinIO link)

MLflow URL: http://192.168.1.162:5001

---

## Output Handling

### Output Location

By default, images upload to MinIO and return a URL:
```
http://192.168.1.215:9000/comfy-gen/<timestamp>_<workflow>_<seed>.png
```

### Local Output

```bash
--output /tmp/my_image.png  # Save locally instead of MinIO
```

### Metadata

```bash
--no-metadata        # Skip JSON sidecar upload
--no-embed-metadata  # Skip PNG embedded metadata
```

### Tagging for Organization

```bash
--project "golden-retriever-study"
--tags "batch:poses,subject:dog,style:photorealistic"
--batch-id "gr-batch-001"
```

---

## Common Patterns

### High-Quality Flux Portrait

```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "Professional headshot portrait of a golden retriever, 
    studio lighting, sharp focus on eyes, shallow depth of field, 
    8K resolution, photorealistic fur detail" \
    --negative-prompt "blurry, low quality, distorted, cartoon" \
    --steps 30 --cfg 3.5 --width 1024 --height 1280 \
    --validate --mlflow-log
```

### NSFW Pony Realism

```bash
python3 generate.py --workflow workflows/pornmaster-pony-stacked-realism.json \
    --prompt "score_9, score_8_up, (beautiful woman:1.4), 
    (photorealistic:1.2), soft lighting" \
    --negative-prompt "score_6, bad anatomy, extra fingers" \
    --lora "add_detail:0.4" --lora "more_details:0.3" \
    --steps 70 --cfg 9.0 --width 768 --height 1280 \
    --mlflow-log --mlflow-experiment "comfy-gen-nsfw"
```

### Quick Draft

```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "quick test concept" \
    --preset draft --no-validate
```

### Batch with Fixed Seed Variations

```bash
for seed in 12345 12346 12347 12348 12349; do
    python3 generate.py --workflow workflows/flux-dev.json \
        --prompt "golden retriever on beach" \
        --seed $seed --mlflow-log
done
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "ComfyUI not responding" | SSH to moira, restart: `python3 scripts/restart_comfyui.py` |
| "Model not found" | Check workflow references correct model filename |
| Low validation score | Increase steps, adjust CFG, improve prompt specificity |
| LoRA not working | Verify base model compatibility in `lora_catalog.yaml` |
| Video too short | Increase `--length` (frames) |
| OOM (out of memory) | Reduce resolution or use `*-low.json` workflow variant |

---

## Files Reference

| File | Purpose |
|------|---------|
| `generate.py` | Main CLI entry point |
| `workflows/*.json` | Workflow definitions |
| `lora_catalog.yaml` | LoRA metadata, compatibility, presets |
| `prompt_catalog.yaml` | Prompt presets, templates |
| `presets.yaml` | Generation presets (draft, balanced, high-quality) |
| `instructions/experiments.md` | Experiment tracking guide |
