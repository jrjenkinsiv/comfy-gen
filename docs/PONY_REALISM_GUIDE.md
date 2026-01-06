# Pony Realism Workflow Guide

> Last Updated: 2026-01-05

This guide documents the optimal workflow for photorealistic NSFW image generation using Pony Realism V2.2 and associated LoRAs.

## Table of Contents
- [Quick Start](#quick-start)
- [Models & LoRAs](#models--loras)
- [Optimal Settings](#optimal-settings)
- [Prompting Strategy](#prompting-strategy)
- [Batch Generation](#batch-generation)
- [Refinement Workflow](#refinement-workflow)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Generate a single high-quality image:

```bash
python3 generate.py \
  --workflow workflows/pony-realism.json \
  --prompt "score_9, score_8_up, score_7_up, rating_explicit, photo, grainy, amateur, 2000s nostalgia, webcam photo, 1girl, nude, blowjob, pov, eye contact, bedroom" \
  --negative-prompt "score_1, score_2, score_3, text, watermark, cartoon, anime" \
  --steps 25 \
  --cfg 6 \
  --lora "zy_AmateurStyle_v2.safetensors:0.8" \
  --output /tmp/test.png
```

---

## Models & LoRAs

### Checkpoint: Pony Realism V2.2
- **File:** `ponyRealism_V22.safetensors` (6.8GB)
- **CivitAI ID:** 372465
- **Base:** SDXL (Pony variant)
- **Strengths:** Photorealistic faces, bodies, skin textures

### Primary LoRA: Pony Amateur Style V2
- **File:** `zy_AmateurStyle_v2.safetensors` (435MB)
- **CivitAI ID:** 480835
- **Strength:** 0.6-1.0 (vary for diversity)
- **Trigger Words:** `photo, grainy, amateur, lowres, 2000s nostalgia, webcam photo, flash`
- **Effect:** Authentic amateur/webcam aesthetic

### Cumshot LoRA: Real Cum SDXL V6.55
- **File:** `realcumv6.55.safetensors` (690MB)
- **CivitAI ID:** 326320
- **Strength:** 0.7-0.8
- **Trigger Words:** None (enhances cum rendering automatically)
- **Use For:** Facial, cum on body, creampie scenes

### Skin Enhancement: Pale Skin SDXL
- **File:** `Pale_Skin_SDXL_v1.0.safetensors`
- **CivitAI ID:** 408526
- **Strength:** 0.3-0.5 (subtle)
- **Trigger Words:** `pale skin`
- **Use For:** Skin tone variation

---

## Optimal Settings

### Sampler Configuration
| Setting | Value | Notes |
|---------|-------|-------|
| Sampler | `dpmpp_2m_sde` | Best for Pony models |
| Scheduler | `karras` | Smooth noise reduction |
| Steps | 25-50 | 25 for quick, 40-50 for HQ |
| CFG | 6 | Higher causes artifacts |
| Resolution | 1024x1024 | Native SDXL resolution |

### LoRA Strength Recommendations
| LoRA | Min | Recommended | Max | Notes |
|------|-----|-------------|-----|-------|
| Amateur Style | 0.6 | 0.8 | 1.0 | Vary for diversity |
| Real Cum | 0.6 | 0.7 | 0.8 | Only for cumshots |
| Pale Skin | 0.3 | 0.4 | 0.5 | Subtle enhancement |

---

## Prompting Strategy

### Quality Tags (REQUIRED)
Always start prompts with quality score tags:
```
score_9, score_8_up, score_7_up, rating_explicit
```

### Style Tags (for Amateur LoRA)
Include these for authentic amateur look:
```
photo, grainy, amateur, 2000s nostalgia, webcam photo
```

### Negative Prompt (Standard)
```
score_1, score_2, score_3, text, watermark, cartoon, anime, drawing, illustration, 3d render, CGI
```

### Weight Syntax
Use parentheses with weights for emphasis:
```
(blowjob:1.4), (pov:1.3), (eye contact:1.2)
```

### Body Type Tags
- `slim body`, `curvy body`, `athletic body`, `busty`
- `thicc thighs`, `milf body`, `petite`, `hourglass figure`

### Ethnicity/Hair Tags
- `caucasian woman`, `latina woman`, `asian woman`, `black woman`
- `mixed race woman`, `redhead woman`, `brunette woman`, `blonde woman`

### Realistic Anatomy Prompts
For better male anatomy rendering:
```
(realistic penis:1.3), (veiny cock:1.2), (erect dick:1.3), (detailed male genitalia:1.2)
```

---

## Batch Generation

### Basic Batch (20 HQ Images)
```bash
python3 scripts/batch_pony_hq.py 1 20
```

### Features
- **Variable LoRA strength:** 0.6, 0.7, 0.8, 0.9, 1.0
- **Variable steps:** 40-50
- **20 scenario types:** Solo, blowjob, doggy, missionary, cowgirl, cumshots, etc.
- **8 body types:** Slim, curvy, athletic, busty, thicc, milf, petite, hourglass
- **8 ethnicities:** Caucasian, latina, asian, black, mixed, redhead, brunette, blonde

### Scenario List
| Category | Scenarios |
|----------|-----------|
| Solo | ass_bent_over, tits_frontal, spread_legs |
| Blowjob | pov, side, deepthroat, cum |
| Doggy | pov, side, prone_bone |
| Missionary | pov, legs_up |
| Cowgirl | pov, reverse |
| Cumshots | facial, tits, body, creampie |
| Other | standing_sex, titfuck, 69_position |

---

## Refinement Workflow

### Purpose
Run generated images through additional img2img passes to enhance detail without changing composition.

### Workflow
```bash
python3 scripts/refine_pony_hq.py --pattern "pony_hq_" --passes 2 --denoise 0.35
```

### Settings
| Setting | Value | Notes |
|---------|-------|-------|
| Denoise | 0.35 | Low to preserve composition |
| Steps | 30 | Per pass |
| LoRA Strength | 0.6 | Lower than generation |
| Passes | 2 | Diminishing returns after 2-3 |

### Refinement Process
1. Download original from MinIO
2. Run img2img pass 1 (denoise 0.35)
3. Run img2img pass 2 (denoise ~0.31, slightly reduced)
4. Upload refined image

---

## Multi-LoRA Combinations

### Basic Generation (Amateur style)
```bash
--lora "zy_AmateurStyle_v2.safetensors:0.8"
```

### Cumshot Scenes (Amateur + Real Cum)
```bash
--lora "zy_AmateurStyle_v2.safetensors:0.8" --lora "realcumv6.55.safetensors:0.7"
```

### Skin Variation (Amateur + Pale Skin)
```bash
--lora "zy_AmateurStyle_v2.safetensors:0.8" --lora "Pale_Skin_SDXL_v1.0.safetensors:0.4"
```

---

## File Locations

### Models (moira: C:\Users\jrjen\comfy\models\)
```
checkpoints/ponyRealism_V22.safetensors
loras/zy_AmateurStyle_v2.safetensors
loras/realcumv6.55.safetensors
loras/Pale_Skin_SDXL_v1.0.safetensors
```

### Workflows
```
workflows/pony-realism.json        # Text-to-image
workflows/pony-realism-refine.json # Img2img refinement
```

### Scripts
```
scripts/batch_pony_hq.py           # High-quality batch generation
scripts/batch_pony_realism.py      # 100-image batch (legacy)
scripts/refine_pony_hq.py          # Refinement passes
```

---

## Troubleshooting

### Cartoony Output
**Problem:** Images look animated/cartoony despite using Pony Realism.

**Solution:** Ensure you're using `source_realistic` tags, NOT `source_anime`:
```
score_9, score_8_up, score_7_up, rating_explicit, photo, grainy, amateur
```

### Fake-Looking Dicks
**Problem:** Male anatomy looks plastic/unrealistic.

**Solution:** Use enhanced prompting:
```
(realistic penis:1.3), (veiny cock:1.2), (erect dick:1.3), (detailed male genitalia:1.2)
```

### Fake-Looking Cum
**Problem:** Cum looks like white paint.

**Solution:** Add Real Cum LoRA:
```bash
--lora "zy_AmateurStyle_v2.safetensors:0.8" --lora "realcumv6.55.safetensors:0.7"
```

With prompt additions:
```
(cum on face:1.5), (thick cum:1.3), (cum dripping:1.2), (messy:1.2)
```

### LoRA Not Found Error
**Problem:** `[ERROR] LoRA not found: ...`

**Solution:** Use separate `--lora` flags, not comma-separated:
```bash
# WRONG:
--lora "lora1.safetensors:0.8,lora2.safetensors:0.7"

# CORRECT:
--lora "lora1.safetensors:0.8" --lora "lora2.safetensors:0.7"
```

### Quality Plateau in Refinement
**Problem:** CLIP scores stop improving after 2-3 passes.

**Solution:** This is expected. Diminishing returns occur around pass 2-3. The bottleneck is model training data, not refinement passes.

---

## CivitAI Model Links

| Model | CivitAI ID | Link |
|-------|------------|------|
| Pony Realism V2.2 | 372465 | https://civitai.com/models/372465 |
| Pony Amateur Style V2 | 480835 | https://civitai.com/models/480835 |
| Real Cum SDXL V6.55 | 326320 | https://civitai.com/models/326320 |
| Pale Skin SDXL | 408526 | https://civitai.com/models/408526 |

---

## Future Improvements

### Not Yet Downloaded
These LoRAs were identified but not downloaded:
- **Pornmaster Pro Pony** (ID 1031307) - Alternative checkpoint
- **Pornmaster Z Image** (ID 2270401) - Different style

### Potential Enhancements
- SDXL/Pony-specific penis LoRA (none found on CivitAI)
- Upscale models for higher resolution output
- ControlNet integration for pose control
