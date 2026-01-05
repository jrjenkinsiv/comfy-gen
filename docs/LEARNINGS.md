# ComfyGen Knowledge Base

This document captures all learnings, tags, model architectures, and experimental findings.

**Last Updated:** 2026-01-04

---

## Model Architecture Compatibility

### Working Architectures (Standard CheckpointLoaderSimple)

| Architecture | Examples | Latent Dimensions | Notes |
|--------------|----------|-------------------|-------|
| **SD 1.5** | majicMIX, Realistic Vision | 512x512 native, scale to 768 | Most LoRAs work. Widest compatibility. |
| **SD 2.x** | SD 2.1 | 768x768 native | Different CLIP. Some LoRAs incompatible. |
| **SDXL** | Pony V6, SDXL Base | 1024x1024 native | Dual CLIP encoders. Requires score tags for Pony. |
| **SD 1.5 Hyper** | Realistic Vision Hyper | 512-768 | Includes baked VAE. Faster inference. |

### NOT Working (Require Special Nodes)

| Architecture | Examples | Why It Fails | What's Needed |
|--------------|----------|--------------|---------------|
| **NextDiT** | PornMaster Z-image | Transformer-based, not UNet | Custom ComfyUI nodes for NextDiT |
| **Flux** | Flux.1 Dev/Schnell | Different architecture | `UNETLoader` + `CLIPTextEncodeFlux` |
| **SD3** | SD 3.0 | New architecture | `ModelSamplingSD3` + Triple CLIP |
| **Wan 2.x** | Wan 2.2 T2V/I2V | Video model | Specialized video workflow |

---

## ComfyUI Loader Node Reference

### Standard Loaders

| Node | Use For | Folder Scanned |
|------|---------|----------------|
| `CheckpointLoaderSimple` | SD 1.5/2/XL checkpoints | `checkpoints/` |
| `UNETLoader` | Standalone UNET/diffusion models | `diffusion_models/` |
| `VAELoader` | Separate VAE files | `vae/` |
| `LoraLoader` | LoRA adapters | `loras/` |
| `CLIPLoader` | CLIP text encoders | `clip/` |

### Specialized Loaders (for transformer models)

| Node | Use For |
|------|---------|
| `DualCLIPLoader` | SDXL (needs 2 CLIP models) |
| `TripleCLIPLoader` | SD3 (needs 3 CLIP models) |
| `QuadrupleCLIPLoader` | Advanced multi-CLIP setups |
| `CLIPTextEncodeFlux` | Flux models |
| `CLIPTextEncodeHunyuanDiT` | HunyuanDiT models |
| `CLIPTextEncodeSD3` | SD3 models |

### Model Sampling Nodes (Required for some architectures)

| Node | Use For |
|------|---------|
| `ModelSamplingDiscrete` | Standard SD models (eps, v_prediction) |
| `ModelSamplingFlux` | Flux models (shift parameters) |
| `ModelSamplingSD3` | SD3 models |
| `ModelSamplingAuraFlow` | AuraFlow models |
| `ModelSamplingContinuousEDM` | EDM-style models |

---

## Prompt Tags & Keywords

### Quality Tags (Universal)

```
masterpiece, best quality, ultra detailed, photorealistic, RAW photo, 8K resolution
```

### Pony V6 XL - REQUIRED Score Tags

**Positive prompt MUST start with:**
```
score_9, score_8_up, score_7_up, [your prompt]
```

**Negative prompt MUST include:**
```
score_4, score_3, score_2, score_1, [your negatives]
```

### Single Person Emphasis (to avoid duplicates)

```
(single woman:1.5), (one person only:1.4), solo
```

**In negative:**
```
multiple people, two people, crowd, duplicate, clone
```

### Camera/Photography Tags

```
Phase One medium format camera, 80mm lens f/1.8, shallow depth of field
Hasselblad H6D, Sony A7R IV, Leica Q2
professional photography, film grain, detailed skin texture
```

### Anatomy Tags (NSFW)

**Female:**
```
full natural breasts, voluptuous hourglass figure, narrow waist, wide hips
```

**Male:**
```
muscular build, broad shoulders, defined muscles, athletic physique
```

### Anti-Quality Tags (Negative)

```
bad quality, blurry, low resolution, watermark, text, deformed, ugly
cartoon, anime, CGI, 3d render, plastic skin, artificial
extra fingers, mutated hands, malformed, bad anatomy, disfigured
```

---

## NSFW/SFW Control

### Observed Behavior

ComfyUI has internal NSFW detection that may affect generation. Tags observed in model metadata:

- `NSFW TRUE` / `NSFW FALSE` - Binary NSFW flag in model files
- Models trained on NSFW content have this baked in

### Models by NSFW Support

| Model | NSFW Training | Quality Score |
|-------|---------------|---------------|
| Realistic Vision V6 | Yes | 0.675 |
| majicMIX Realistic | Yes | 0.674 |
| Pony V6 XL | Yes (anime+realistic) | 0.664 |
| SD 1.5 Base | Censored | 0.55 |

---

## LoRA Stacking

### Recommended Stack for Detail

```bash
--lora "more_details.safetensors:0.5" --lora "add_detail.safetensors:0.4"
```

**Order matters:** Apply detail LoRAs after style LoRAs.

### Strength Guidelines

| LoRA Type | Recommended Strength |
|-----------|---------------------|
| Detail enhancement | 0.3-0.5 |
| Style transfer | 0.6-0.8 |
| Character consistency | 0.7-0.9 |
| Body modification | 0.5-0.7 |

---

## CLIP Token Limits

### Problem
CLIP has a **77-token hard limit** (`max_position_embeddings`).

### Solution: Prompt Chunking
Our `generate.py` implements AUTOMATIC1111-style chunking:
1. Split prompt at 75 tokens (leave 2 for special tokens)
2. Encode each chunk separately
3. Concatenate embeddings

### Best Practice
- Longer prompts now IMPROVE quality (with chunking)
- Use detailed, verbose descriptions (100-200 tokens)
- Repeat important constraints with different phrasing

---

## Sampler & Scheduler Combinations

### Recommended for Photorealism

```
--sampler dpmpp_sde --scheduler karras
```

### Fast Preview

```
--sampler euler --scheduler normal --steps 20
```

### High Quality

```
--sampler dpmpp_2m --scheduler karras --steps 50
```

---

## Available Models (Current Inventory)

### Checkpoints (Working)

| Filename | Type | Score |
|----------|------|-------|
| `realisticVisionV60B1_v51HyperVAE.safetensors` | SD 1.5 Hyper | 0.675 |
| `majicmixRealistic_v7.safetensors` | SD 1.5 | 0.674 |
| `ponyDiffusionV6XL_v6StartWithThisOne.safetensors` | SDXL/Pony | 0.664 |
| `v1-5-pruned-emaonly-fp16.safetensors` | SD 1.5 | ~0.55 |

### Diffusion Models (Specialized)

| Filename | Type | Notes |
|----------|------|-------|
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | Wan 2.2 T2V | Video generation |
| `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` | Wan 2.2 T2V | Video generation |
| `NSFW-22-H-e8.safetensors` | Wan 2.2 NSFW LoRA | High noise variant |
| `NSFW-22-L-e8.safetensors` | Wan 2.2 NSFW LoRA | Low noise variant |

### LoRAs

| Filename | Compatible With | Use |
|----------|----------------|-----|
| `more_details.safetensors` | SD 1.5/SDXL | Detail enhancement |
| `add_detail.safetensors` | SD 1.5/SDXL | Complementary detail |
| `big_breasts_v2_epoch_30.safetensors` | SD 1.5 | Body modification |

---

## Experimental Findings

### Duplicate Person Issue
- **Cause:** Model tendency + prompt ambiguity
- **Solution:** Strong emphasis `(single:1.5)` + negative `multiple people`
- **Status:** Partially mitigated, not fully solved

### Score System
Our CLIP-based validation:
- 0.65+ = Good match
- 0.60-0.65 = Acceptable
- <0.60 = Poor match

### CFG Scale
- 7.0 = Default, balanced
- 8.5 = Stricter prompt adherence
- 5.0 = More creative freedom
- 10.0+ = Risk of oversaturation

---

## Future Research

### Models to Try
- epiCRealism (highly rated on CivitAI)
- DreamShaper (versatile)
- CyberRealistic (modern photorealism)

### Architectures to Explore
- Flux.1 (requires custom workflow)
- SD3.5 (when available)
- HunyuanDiT (Chinese aesthetic)

### Custom Nodes Needed
For NextDiT/Z-image models, we'd need to install:
- ComfyUI-NextDiT custom nodes
- Specific sampling nodes for the architecture
