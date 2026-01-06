# NSFW Generation Guide

**Last verified:** 2026-01-05

Complete reference for generating explicit adult content with ComfyGen. Covers model selection, prompting techniques, LoRA usage, and quality optimization.

---

## Table of Contents

- [Core Principles](#core-principles)
- [Model Selection](#model-selection)
  - [Image Models](#image-models)
  - [Video Models](#video-models)
- [LoRA Configuration](#lora-configuration)
  - [Verified LoRAs](#verified-loras)
  - [CRITICAL: Video vs Image LoRAs](#critical-video-vs-image-loras)
  - [Stacking Strategy](#stacking-strategy)
- [Prompt Engineering](#prompt-engineering)
  - [Terminology](#terminology)
  - [Prompt Weighting](#prompt-weighting)
  - [Anatomical Specifications](#anatomical-specifications)
  - [POV Technique](#pov-technique)
- [Technical Settings](#technical-settings)
  - [Steps and CFG](#steps-and-cfg)
  - [Resolution Guidelines](#resolution-guidelines)
- [Example Prompts](#example-prompts)
- [Quality Enhancement](#quality-enhancement)
- [Troubleshooting](#troubleshooting)
- [Experiment Log](#experiment-log)

---

## Core Principles

**Terminology:** Use explicit/colloquial terms over clinical language. Models are trained on internet data where vulgar terms dominate in NSFW contexts.

**Model Matching:** Always verify LoRA base model compatibility. Using a Wan 2.2 video LoRA for SD 1.5 image generation causes severe distortions.

**Quality Over Speed:** NSFW content with complex anatomy benefits from higher step counts (50-80) and moderate CFG (8.0-9.5).

---

## Model Selection

### Image Models

| Model | Base | Strengths | Use Case |
|-------|------|-----------|----------|
| **MajicMix Realistic v7** | SD 1.5 | Photorealistic skin, natural lighting | Portraits, realistic scenes |
| **Realistic Vision** | SD 1.5 | Consistent anatomy, good detail | General photorealistic |
| **Pony Diffusion V6** | SDXL | Stylized look, good anatomy variety | Artistic/semi-realistic |
| **RealVisXL V4.0** | SDXL | Excellent skin tones, photorealism | High-res portraits |
| **Juggernaut XL** | SDXL | Strong anatomical accuracy | Detailed body shots |

**Workflow files:**
- `workflows/majicmix-realistic.json` - SD 1.5 photorealistic
- `workflows/realistic-vision.json` - SD 1.5 realistic
- `workflows/pony-v6.json` - SDXL stylized
- `workflows/flux-dev.json` - Flux (general purpose)

### Video Models

| Model | Type | Use Case |
|-------|------|----------|
| **Wan 2.2 t2v** | Text-to-video | Generate video from prompt |
| **Wan 2.2 i2v** | Image-to-video | Animate existing image |

**Workflow files:**
- `workflows/wan22-t2v.json` - Text to video
- `workflows/wan22-i2v.json` - Image to video

---

## LoRA Configuration

### Verified LoRAs

**SD 1.5 Image LoRAs (CivitAI Verified):**

| LoRA | CivitAI ID | Trigger Words | Strength |
|------|------------|---------------|----------|
| `airoticart_penis.safetensors` | 15040 | `penerec` (erect), `penflac` (flaccid) | 0.8-0.9 |
| `polyhedron_skin.safetensors` | 109043 | `detailed skin`, `skin blemish` | 0.4-0.6 |
| `realora_skin.safetensors` | 137258 | (none needed) | 0.4-0.5 |
| `more_details.safetensors` | 82098 | (none needed) | 0.3-0.5 |
| `add_detail.safetensors` | 58390 | (none needed) | 0.3-0.5 |

**Wan 2.2 Video LoRAs (DO NOT use for images):**

| LoRA | Trigger Words |
|------|---------------|
| `erect_penis_epoch_80.safetensors` | `penis` |
| `deepthroat_epoch_80.safetensors` | `blowjob`, `deepthroat` |
| `big_breasts_v2_epoch_30.safetensors` | `big breasts` |
| `doggyPOV_v1_1.safetensors` | `POVdog` |

### CRITICAL: Video vs Image LoRAs

**NEVER use Wan 2.2 video LoRAs for image generation.**

This causes:
- Distorted anatomy (weird breasts, floating body parts)
- Merged/duplicated features
- Poor quality output

**How to verify:**

```bash
# Get SHA256 hash from moira
ssh moira "powershell -Command \"(Get-FileHash -Algorithm SHA256 '<path>').Hash\""

# Look up on CivitAI API
curl "https://civitai.com/api/v1/model-versions/by-hash/<HASH>"
```

The `baseModel` field in the response tells you: `SD 1.5`, `SDXL`, `Wan Video 14B t2v`, etc.

See [LORA_GUIDE.md](LORA_GUIDE.md) for complete verification process.

### Stacking Strategy

Order matters. Apply LoRAs in this sequence:

1. **Anatomy LoRA first** (strength 0.8-0.9)
2. **Skin/detail LoRAs second** (strength 0.4-0.6)
3. **Total combined strength** should not exceed ~1.5

```bash
python3 generate.py \
    --workflow workflows/majicmix-realistic.json \
    --prompt "..." \
    --lora "airoticart_penis.safetensors:0.85" \
    --lora "polyhedron_skin.safetensors:0.5" \
    --lora "add_detail.safetensors:0.3" \
    --output /tmp/output.png
```

---

## Prompt Engineering

### Terminology

Models respond better to explicit/colloquial terms:

| Use This | Not This |
|----------|----------|
| cock, dick | penis |
| cum, cumshot | semen, ejaculation |
| pussy | vagina |
| tits, boobs | breasts |
| balls | testicles |
| ballsack | scrotum |

### Prompt Weighting

Use parentheses and colons to emphasize:

| Syntax | Effect |
|--------|--------|
| `(keyword:1.2)` | Slight emphasis |
| `(keyword:1.3-1.4)` | Strong emphasis |
| `(keyword:1.5-1.8)` | Maximum (watch for artifacts) |

Stack related terms for reinforcement:
```
(uncut:1.3), (foreskin:1.3), uncircumcised, natural
```

### Anatomical Specifications

**Uncircumcised + Flaccid + Veiny:**

```
Positive:
(uncut cock:1.4), (foreskin:1.3), flaccid, soft dick, (veiny cock:1.3), 
prominent veins, thick veins, vascular detail, (hanging balls:1.3), 
low hangers, heavy balls, wrinkled ballsack, precum dripping, leaking, 
glistening, natural anatomy, detailed texture, photorealistic, 8k detail

Negative:
erect, hard, circumcised, cut, smooth, no veins, hairless, plastic skin, 
fake, cartoon, 3D render, bad anatomy, deformed
```

**Large Natural Breasts:**

```
Positive:
(large natural tits:1.3), (big breasts:1.2), natural sag, realistic breast shape, 
soft breasts, natural hang, detailed skin texture, visible pores, areola detail, 
photorealistic

Negative:
fake tits, implants, bolt-ons, perky, anime, cartoon, plastic, 
perfect spheres, unrealistic shape
```

### POV Technique

SD 1.5 models struggle with two distinct human bodies. Use POV (point of view) prompts:

**Instead of:**
```
woman sucking man's cock, man standing  # BAD - two bodies
```

**Use:**
```
(POV shot:1.4), (first person perspective:1.3), 
woman sucking cock, cock entering from bottom of frame,
viewer's cock, looking up at camera  # GOOD - one visible body
```

**Key POV markers:**
- `(POV shot:1.4)` - Main perspective marker
- `(first person perspective:1.3)` - Reinforcement
- `cock entering from bottom of frame` - Spatial positioning
- `viewer's cock` - Establishes ownership

**Add to negative:**
```
man's body visible, standing man, full male body
```

---

## Technical Settings

### Steps and CFG

| Quality Level | Steps | CFG | Use Case |
|---------------|-------|-----|----------|
| Draft | 30-40 | 7.0 | Quick testing |
| Standard | 50-60 | 8.0-9.0 | Normal batch runs |
| High Quality | 70-80 | 8.5-9.5 | Final outputs |

**CFG Guidelines:**
- 7.0-8.0: More creative, can drift from prompt
- 8.5-9.5: Stricter prompt adherence (recommended for NSFW)
- 10.0+: Very strict, can cause artifacts

### Resolution Guidelines

| Aspect | Resolution | Use Case |
|--------|------------|----------|
| Square | 1024x1024 | General purpose |
| Portrait | 768x1024, 1024x1536 | Full body, portraits |
| Landscape | 1536x1024 | POV shots, scenes |

For SD 1.5 models, stay within 512-768 on shortest side.

---

## Example Prompts

### Scene Example: Kneeling Position with Cumshot

**Positive:**
```
(Asian woman:1.2), (kneeling:1.2), on her knees, (looking up at camera:1.1), 
(large natural tits:1.3), big breasts, natural sag, (cum on tits:1.4), 
(cumshot:1.3), thick cum, cum dripping, cum strands, creamy white cum, 
glistening, wet breasts, realistic cum texture, detailed skin, pores visible, 
natural lighting, soft lighting, photorealistic, 8k, sharp focus, 
(POV angle:1.2), close-up upper body, black hair, long hair, beautiful face, 
detailed eyes, submissive expression, mouth slightly open
```

**Negative:**
```
erect nipples, fake tits, implants, standing, clothed, censored, blurred, 
mosaic, cartoon, anime, 3D render, plastic skin, oversaturated, bad anatomy, 
deformed, extra limbs, watermark, text
```

**Settings:**
- Steps: 60-70
- CFG: 8.5-9.0
- Sampler: DPM++ 2M Karras
- Resolution: 1024x1536 (portrait)

### Complete Command Example

```bash
python3 generate.py \
    --workflow workflows/majicmix-realistic.json \
    --prompt "(Asian woman:1.2), (kneeling:1.2), on her knees, (looking up at camera:1.1), (large natural tits:1.3), big breasts, natural sag, detailed skin, pores visible, natural lighting, soft lighting, photorealistic, 8k, sharp focus, (POV angle:1.2), close-up upper body, black hair, long hair, beautiful face, detailed eyes" \
    --negative-prompt "fake tits, implants, standing, clothed, censored, blurred, cartoon, anime, 3D render, plastic skin, oversaturated, bad anatomy, deformed, extra limbs, watermark, text" \
    --steps 60 \
    --cfg 9.0 \
    --width 768 \
    --height 1024 \
    --lora "polyhedron_skin.safetensors:0.5" \
    --output /tmp/portrait.png
```

---

## Quality Enhancement

### Upscaling Workflow

1. Generate at base resolution (1024x1024 or similar)
2. Use **Ultimate SD Upscale** node in ComfyUI
3. Scale: 1.5-2x
4. Tile size: 512-768
5. Adds vein detail, skin texture, cum texture

### Detail LoRAs

Apply at 0.3-0.5 strength for enhancement:
- `add_detail.safetensors`
- `more_details.safetensors`
- `polyhedron_skin.safetensors`

---

## Troubleshooting

### Problem: Getting circumcised when you want uncut

**Solutions:**
- Increase weight: `(uncut:1.5)`, `(foreskin:1.4)`
- Add to negative: `circumcised, cut, no foreskin`
- Try European ethnicity tags

### Problem: Always erect instead of flaccid

**Solutions:**
- Increase: `(flaccid:1.4)`, `(soft:1.3)`
- Add: `relaxed state, hanging, drooping`
- Negative: `erect, hard, stiff, aroused`

### Problem: Not enough veins

**Solutions:**
- Use vascular LoRAs at 0.6-0.8 strength
- Prompt: `(extremely veiny:1.5), thick prominent veins`
- Upscale with detail enhancement

### Problem: Unrealistic cum texture

**Solutions:**
- Prompt: `thick cum, creamy cum, realistic cum texture, viscous`
- Reference real cumshot images with img2img at low denoise
- Some models have "cum texture" LoRAs

### Problem: Duplicate/merged people

**Solutions:**
- Use POV technique (see above)
- Add to prompt: `solo, one person, single subject`
- Add to negative: `two people, multiple people, crowd`
- Use portrait orientation (768x1024)
- Consider ControlNet with single-person pose

### Problem: Using wrong LoRA type

**Symptoms:**
- Distorted anatomy
- Floating body parts
- Merged features

**Solution:**
Always verify LoRA base model before use:
```bash
ssh moira "powershell -Command \"(Get-FileHash -Algorithm SHA256 '<path>').Hash\""
curl "https://civitai.com/api/v1/model-versions/by-hash/<HASH>"
```

---

## Experiment Log

### Massive Experiment Results (2026-01-05)

**Run Summary:**
- **Total experiments:** 250
- **Successful generations:** 18 (7.2%)
- **Primary failure cause:** ComfyUI server disconnected mid-run

**Successful Parameters (18 images that worked):**

| Scenario | Ethnicity | Sampler | Steps | LoRA Preset |
|----------|-----------|---------|-------|-------------|
| nude_portrait | middle_eastern | euler | 120 | amateur_grainy |
| lingerie_tease | korean | dpmpp_2s_ancestral | 30 | amateur_grainy |
| wet_shower | brazilian | dpmpp_sde | 50 | realism_basic |
| facefuck | russian | dpmpp_2s_ancestral | 30 | amateur_grainy |
| two_hand_blowjob | russian | euler_ancestral | 150 | nsfw_action |
| sloppy_blowjob | chinese | dpmpp_2s_ancestral | 30 | realism_enhanced |
| facefuck | african_american | dpmpp_2m_sde | 80 | nsfw_detailed |
| spooning | japanese | dpmpp_2s_ancestral | 120 | nsfw_detailed |
| standing_sex | caucasian_redhead | dpmpp_sde | 30 | skin_focus |
| doggy_style | mediterranean | dpmpp_2s_ancestral | 80 | nsfw_detailed |
| cowgirl | korean | dpmpp_2m | 80 | nsfw_detailed |
| doggy_style | thai | dpmpp_sde | 30 | nsfw_action |
| reverse_cowgirl | caucasian_blonde | uni_pc | 150 | nsfw_detailed |
| cum_on_back | african_american | dpmpp_2m_sde | 30 | cumshot_realistic |
| cum_on_tits | vietnamese | dpmpp_2s_ancestral | 50 | cumshot_heavy |
| cum_on_ass | vietnamese | dpmpp_sde | 30 | cumshot_heavy |
| lesbian_kiss | thai | ddim | 30 | high_detail |

**Key Learnings:**

1. **Sampler patterns:** `dpmpp_2s_ancestral` and `dpmpp_sde` appear most frequently in successful runs
2. **Step range:** 30-120 steps produced good results; no clear correlation with quality
3. **LoRA presets:** `nsfw_detailed`, `amateur_grainy`, and `cumshot_*` presets worked well
4. **Ethnicities:** Korean, Vietnamese, Russian, Thai appeared frequently in successes
5. **Auto-upload:** `generate.py` automatically uploads to MinIO - no separate uploader needed

**Technical Issues Identified:**

| Issue | Cause | Mitigation |
|-------|-------|------------|
| 92.8% failure rate | ComfyUI crashed/disconnected | Add health checks before each generation |
| Empty error messages | Script didn't capture stderr properly | Improve error capture in experiment scripts |
| No retry mechanism | Single-pass design | Add `--retry-failed` flag to experiment scripts |

### Previous Observations (2026-01-04)

**Models Tested:**

| Model | Type | Result |
|-------|------|--------|
| MajicMix Realistic v7 | SD 1.5 | Realistic skin/lighting. Some duplicate person issues. |
| Pony Realism | SDXL/Pony | **Best results.** Photorealistic, good anatomy, no merge issues. |
| Pony V6 | SDXL | More stylized. Consistent faces. |

**Known Issues:**
- SD 1.5 models can produce merged/stacked people despite "solo" prompts
- CLIP validation (0.6-0.7) passes even for problematic images
- Higher CFG alone does not prevent duplicates

**What Works:**
- **Pony Realism workflow** - Most consistent photorealistic results
- POV prompting significantly reduces two-body issues
- Portrait orientation helps with single-subject
- Skin LoRAs at moderate strength (0.4-0.6) improve realism
- Anti-TS negative: `trans, transgender, futanari, futa, hermaphrodite, shemale, dickgirl`

### Running Experiments

See [EXPERIMENTS.md](EXPERIMENTS.md) for:
- How to run batch experiments
- Retrying failed experiments
- Analyzing results
- MLflow integration

### Open Issues

See GitHub issues:
- #131 - Video generation pipeline integration
- #129 - LoRA strength experimentation script
- #127 - Find SDXL/Pony realistic penis LoRA
- #82 - Test ControlNet for single-person enforcement
- #83 - Test additional realistic models
- #80 - Analyze validation threshold
- #85 - Add vision model content validation

---

## Related Documentation

- [LORA_GUIDE.md](LORA_GUIDE.md) - Complete LoRA selection and verification
- [QUALITY_SYSTEM.md](QUALITY_SYSTEM.md) - Quality scoring and validation
- [USAGE.md](USAGE.md) - General CLI usage
- [MODEL_REGISTRY.md](MODEL_REGISTRY.md) - Installed models inventory

---

**Documentation Policy:** This is an authoritative reference document. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only.
