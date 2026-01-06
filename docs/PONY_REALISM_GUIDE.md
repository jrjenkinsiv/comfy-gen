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

### Male Anatomy Prompting (No LoRA Available)

**Important:** No SDXL/Pony-compatible penis LoRA exists (as of 2026-01-06). Use comprehensive weight-based prompting instead.

#### Quick Reference (Copy-Paste Ready)
```
# Basic (moderate realism):
(realistic penis:1.3), (veiny cock:1.2), (erect dick:1.3), (detailed male genitalia:1.2)

# Advanced (maximum realism - use for close-ups or anatomy focus):
(realistic penis:1.4), (veiny cock:1.3), (detailed shaft:1.2), (natural skin texture:1.3), (anatomically correct:1.2), (photorealistic genitals:1.3), (detailed glans:1.2), (natural penis:1.3)

# Negative prompt additions:
cartoon penis, plastic looking, smooth like doll, unrealistic anatomy, toy-like, artificial, CGI genitals
```

#### Tips
- Use CFG 8-9 (instead of 6) for better anatomy adherence
- Stack 5-8 descriptors with varied weights
- Use colloquial terms ("cock", "dick") - models trained on internet data
- Combine with `zy_AmateurStyle_v2.safetensors:0.8` for overall realism

See **Troubleshooting > Fake-Looking Dicks** section for comprehensive examples and context-specific strategies.

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
**Problem:** Male anatomy looks plastic/unrealistic even with Pony Realism.

**Research:** No SDXL/Pony-specific penis LoRA exists on CivitAI or HuggingFace as of 2026-01-06. The only verified realistic penis LoRA (`airoticart_penis.safetensors`) is SD 1.5 only and INCOMPATIBLE with Pony.

**Solution:** Use comprehensive weight-based prompting:

#### Basic Approach (Moderate Realism)
```
(realistic penis:1.3), (veiny cock:1.2), (erect dick:1.3), (detailed male genitalia:1.2)
```

#### Advanced Approach (Maximum Realism)
Stack multiple descriptors with varied weights:
```
(realistic penis:1.4), (veiny cock:1.3), (detailed shaft:1.2), (natural skin texture:1.3), 
(anatomically correct:1.2), (photorealistic genitals:1.3), (circumcised:1.1), 
(erect male anatomy:1.3), (detailed glans:1.2), (natural penis:1.3)
```

#### Context-Specific Prompting
For different scenarios, emphasize different aspects:

**Close-up shots:**
```
(detailed penis close-up:1.5), (macro shot:1.3), (skin pores visible:1.2), 
(veiny texture:1.4), (realistic glans:1.3), (natural lighting:1.2)
```

**POV scenes:**
```
(pov realistic penis:1.4), (first person view:1.3), (natural perspective:1.2), 
(detailed cock:1.3), (photorealistic shaft:1.3)
```

**Full body with anatomy visible:**
```
(realistic male body:1.3), (natural genitals:1.3), (anatomically correct nude:1.2), 
(photorealistic penis:1.3), (natural proportions:1.2)
```

#### Negative Prompting Strategy
Add these to negative prompt to avoid common issues:
```
cartoon penis, plastic looking, smooth like doll, unrealistic anatomy, 
toy-like, artificial, CGI genitals, smooth texture, featureless
```

#### Tips for Best Results
1. **Use colloquial terms:** Models are trained on internet data - "cock" and "dick" often work better than "penis"
2. **Layer descriptors:** Use 5-8 different terms with varied weights rather than one heavily-weighted term
3. **Combine with Amateur LoRA:** `zy_AmateurStyle_v2.safetensors:0.8` improves overall realism
4. **Higher CFG for anatomy:** Use CFG 8-9 instead of 6 for stricter adherence to anatomy prompts
5. **Add reference context:** Terms like "photorealistic", "natural lighting", "skin texture" help overall realism

#### Example Full Prompt
```bash
python3 generate.py \
  --workflow workflows/pony-realism.json \
  --prompt "score_9, score_8_up, score_7_up, rating_explicit, photo, grainy, amateur, 2000s nostalgia, webcam photo, pov blowjob, (realistic penis:1.4), (veiny cock:1.3), (detailed shaft:1.2), (natural skin texture:1.3), (photorealistic genitals:1.3), (detailed glans:1.2), eye contact, bedroom" \
  --negative-prompt "score_1, score_2, score_3, cartoon penis, plastic looking, smooth like doll, unrealistic anatomy, text, watermark" \
  --steps 40 \
  --cfg 8.5 \
  --lora "zy_AmateurStyle_v2.safetensors:0.8" \
  --output /tmp/realistic_anatomy.png
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

### Male Anatomy LoRA Research (2026-01-06)
**Searches conducted:**
- CivitAI: 'pony penis realistic', 'sdxl penis', 'male anatomy pony', 'photorealistic male', 'realistic anatomy', 'adult male body'
- HuggingFace: SDXL male anatomy searches
- Pony-specific model pages

**Finding:** No SDXL/Pony-compatible realistic penis LoRA exists as of 2026-01-06.

**Available LoRAs (INCOMPATIBLE):**
- `airoticart_penis.safetensors` - SD 1.5 only (CivitAI ID 15040)
- `erect_penis_epoch_80.safetensors` - Wan 2.2 Video only (CivitAI verified)
- `dicks_epoch_100.safetensors` - Wan 2.2 Video only (CivitAI verified)

**Workaround:** Use comprehensive weight-based prompting (see "Fake-Looking Dicks" troubleshooting section).

### Potential Enhancements
- SDXL/Pony-specific penis LoRA (none currently available - may need custom training)
- Upscale models for higher resolution output
- ControlNet integration for pose control
