# Model Registry

**Last verified:** 2026-01-05

This document tracks all models and LoRAs installed on moira for ComfyUI.

**Last Updated:** 2026-01-04  
**Model Directory:** `C:\Users\jrjen\comfy\models\`

## Quick Download

Use the download script for easy model installation:

```bash
# Search for models
python scripts/download_model.py --search "realistic" --type checkpoint --limit 10

# Download by CivitAI model ID
python scripts/download_model.py --model-id 43331 --type checkpoint

# Download by specific version ID
python scripts/download_model.py --version-id 176425 --type checkpoint

# Download a LoRA
python scripts/download_model.py --model-id 82098 --type lora

# Dry-run (show info without downloading)
python scripts/download_model.py --model-id 43331 --type checkpoint --dry-run
```

**Supported types:** `checkpoint`, `lora`, `vae`, `embedding`, `hypernetwork`

## API Key Setup

Models can be downloaded from multiple sources:

| Source | Auth Required | Config |
|--------|---------------|--------|
| CivitAI | Yes (many models) | `CIVITAI_API_KEY` in `.env` |
| HuggingFace | Yes (gated models) | `HF_TOKEN` in `.env` |
| Direct URL | No | Just use URL |

**Setup (one-time):**
```bash
# Create .env file in project root (gitignored)
echo "CIVITAI_API_KEY=your_key_here" >> .env
echo "HF_TOKEN=hf_your_token_here" >> .env
```

## Directory Structure

```
C:\Users\jrjen\comfy\models\
├── checkpoints/      # Base models (SD 1.5, SDXL, Flux, Wan)
├── loras/            # LoRA adapters  
├── vae/              # VAE models
├── text_encoders/    # T5, CLIP encoders
├── diffusion_models/ # Wan 2.2 diffusion models
├── unet/             # UNet models
├── embeddings/       # Textual inversions
└── sams/             # Segment Anything models
```

---

## Checkpoints (Base Models)

### Currently Installed (Verified Working)

| Filename | Type | Size | Workflow | Score | Notes |
|----------|------|------|----------|-------|-------|
| `realisticVisionV60B1_v51HyperVAE.safetensors` | SD 1.5 Hyper | 4GB | `realistic-vision.json` | 0.675 | **TOP** Best photorealism, includes VAE. |
| `majicmixRealistic_v7.safetensors` | SD 1.5 | 2GB | `majicmix-realistic.json` | 0.674 | Excellent for portraits/NSFW. 1.1M+ downloads. |
| `ponyDiffusionV6XL_v6StartWithThisOne.safetensors` | SDXL/Pony | 6.6GB | `pony-v6.json` | 0.664 | SDXL-based. Use score_9 tags. Native 1024x1024. |
| `v1-5-pruned-emaonly-fp16.safetensors` | SD 1.5 | 2GB | `flux-dev.json` | ~0.55 | Baseline model. Fast but lower quality. |

### Pony Diffusion V6 XL - Special Tags

Pony requires special quality tags in the prompt:
```
Positive: score_9, score_8_up, score_7_up, [your prompt here]
Negative: score_4, score_3, score_2, score_1, [your negatives]
```

### Models NOT Working

| Model | Issue | Reason |
|-------|-------|--------|
| PornMaster Z-image | NextDiT architecture | Requires custom ComfyUI nodes not installed |
| Any NextDiT/Transformer models | Incompatible | Standard workflows don't support NextDiT |

### Recommended Downloads

```bash
# Realistic checkpoints (highly rated on CivitAI)
python scripts/download_model.py --model-id 25694 --type checkpoint  # epiCRealism (816K downloads)
python scripts/download_model.py --model-id 4384 --type checkpoint   # DreamShaper (high quality)
```

## Diffusion Models

| Filename | Type | Notes |
|----------|------|-------|
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | Wan 2.2 T2V | Text-to-video, high noise |
| `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` | Wan 2.2 T2V | Text-to-video, low noise |
| `wan_2.1_vae.safetensors` | Wan 2.1 VAE | Video VAE |
| `cosmos_predict2_2B_video2world_480p_16fps.safetensors` | Cosmos | Video generation |

## Text Encoders

| Filename | Type | Notes |
|----------|------|-------|
| `oldt5_xxl_fp8_e4m3fn_scaled.safetensors` | T5-XXL | FP8 quantized |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | UMT5-XXL | FP8 quantized |

## VAE Models

| Filename | Type | Notes |
|----------|------|-------|
| `sdxl_vae.safetensors` | SDXL VAE | For SDXL/Pony models (ponyDiffusionV6XL) |
| `wan_2.1_vae.safetensors` | Wan VAE | For Wan video models |
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | Wan VAE | Alternate VAE |

## SAM Models

| Filename | Type | Notes |
|----------|------|-------|
| `sam_vit_b_01ec64.pth` | SAM ViT-B | Segment Anything base |

## LoRAs

LoRA files are stored in `C:\Users\jrjen\comfy\models\loras\`.

**Note:** LoRA inventory is maintained locally. Many LoRAs are for specialized content generation.

### Acceleration LoRAs (Reduce Steps)

| Filename | Compatible With | Notes |
|----------|----------------|-------|
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` | Wan 2.2 T2V High | 4-step acceleration |
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors` | Wan 2.2 T2V Low | 4-step acceleration |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | Wan 2.2 I2V High | 4-step acceleration |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | Wan 2.2 I2V Low | 4-step acceleration |
| `Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors` | Wan 2.2 I2V | 4-step Seko |

### Detail Enhancement LoRAs

| Filename | Compatible With | Strength | Notes |
|----------|----------------|----------|-------|
| `more_details.safetensors` | SD 1.5/SDXL | 0.5 | Adds fine detail to faces/skin. Stack with add_detail. |
| `add_detail.safetensors` | SD 1.5/SDXL | 0.4 | Complementary detail enhancement. Use after more_details. |

### Physics/Motion LoRAs

| Filename | Compatible With | Notes |
|----------|----------------|-------|
| `BoobPhysics_WAN_v6.safetensors` | Wan 2.2 | Physics enhancement |
| `BounceHighWan2_2.safetensors` | Wan 2.2 High | Motion enhancement |
| `BounceLowWan2_2.safetensors` | Wan 2.2 Low | Motion enhancement |
| `wan-thiccum-v3.safetensors` | Wan 2.2 | Body enhancement |

### Game Asset LoRAs (Icons, Sprites, UI)

| Filename | Compatible With | Notes |
|----------|----------------|-------|
| `vector_icons_game_assets.safetensors` | SD 1.5 | Vector-style game icons, flat design. Strength 0.8. Source: CivitAI 2251918 |
| `PixelArtRedmond15V-PixelArt-PIXARFK.safetensors` | SD 1.5 | Pixel art style. Trigger: "pixarfk". Source: HuggingFace artificialguybr |
| `GothicPixelArtV1.1.safetensors` | SD 1.5 | Gothic/dark pixel art style. Strength 0.8. Source: CivitAI 2264335 |

**Game Asset Usage Notes:**
- Use with SD 1.5 workflow (`flux-dev.json` uses v1-5-pruned-emaonly-fp16)
- Best for top-down views of ships, icons, UI elements
- Recommended negative prompt: "realistic, 3d, photograph, perspective"
- See `lora_catalog.yaml` for the `battleship_ship_icon` preset

### NSFW/Adult LoRAs (18+)

**Note:** NSFW LoRAs are cataloged in `lora_catalog.yaml` with `category: "nsfw"` tag.
These are stored locally only and never uploaded to GitHub or public locations.

Categories include:
- Wan 2.2 T2V/I2V adult content (high/low noise variants)
- Flux/SD adult anatomy and action LoRAs
- Physics/motion enhancement LoRAs

See `lora_catalog.yaml` for full inventory with compatibility info.

---

## Configuration: extra_model_paths.yaml

ComfyUI uses `extra_model_paths.yaml` to find models. This file should be in the ComfyUI directory:

**Location:** `C:\Users\jrjen\AppData\Local\Programs\@comfyorgcomfyui-electron\resources\ComfyUI\extra_model_paths.yaml`

**Content:**
```yaml
comfyui:
  base_path: C:/Users/jrjen/comfy/
  checkpoints: models/checkpoints/
  clip: models/clip/
  clip_vision: models/clip_vision/
  configs: models/configs/
  controlnet: models/controlnet/
  diffusers: models/diffusers/
  embeddings: models/embeddings/
  gligen: models/gligen/
  hypernetworks: models/hypernetworks/
  loras: models/loras/
  style_models: models/style_models/
  unet: models/unet/
  upscale_models: models/upscale_models/
  vae: models/vae/
  vae_approx: models/vae_approx/
  text_encoders: models/text_encoders/
  diffusion_models: models/diffusion_models/
  sams: models/sams/
```

This config tells ComfyUI to look in `C:\Users\jrjen\comfy\models\` for all model types, keeping everything in ONE location.

---

## Usage Examples

### Text-to-Video with Wan 2.2

Generate a video from a text prompt:

```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a person walking through a park on a sunny day" \
    --output /tmp/video.mp4
```

The workflow uses:
- **Model:** `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors`
- **Text Encoders:** `oldt5_xxl_fp8_e4m3fn_scaled.safetensors`
- **VAE:** `wan_2.1_vae.safetensors`
- **Acceleration LoRA:** `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` (4 steps)
- **Output:** 848x480, 81 frames, 8 fps (~10 seconds)

### Image-to-Video with Wan 2.2

Animate an existing image:

```bash
python3 generate.py \
    --workflow workflows/wan22-i2v.json \
    --prompt "the person starts walking forward" \
    --output /tmp/animated.mp4
```

The workflow uses:
- **Model:** `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors`
- **Acceleration LoRA:** `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` (4 steps)
- **Input:** Load your image via ComfyUI or modify the workflow

**Note:** The I2V workflow requires an input image. Update node 5 in `wan22-i2v.json` with your image path or upload via ComfyUI.

### SD 1.5 Image Generation

For simple image generation:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a beautiful mountain landscape at sunset" \
    --output /tmp/landscape.png
```

---

## Adding New Models

### Model Sources

1. **Hugging Face**: https://huggingface.co/models
2. **CivitAI**: https://civitai.com/
3. **Official Repositories**: Check model documentation

### Installation Steps

1. **Download model** to appropriate subdirectory in `C:\Users\jrjen\comfy\models\`:
   ```powershell
   # On moira (Windows)
   # For checkpoints:
   curl -L <model_url> -o "C:\Users\jrjen\comfy\models\checkpoints\model_name.safetensors"
   
   # For LoRAs:
   curl -L <lora_url> -o "C:\Users\jrjen\comfy\models\loras\lora_name.safetensors"
   ```

2. **Update this registry** with filename, type, and notes

3. **Restart ComfyUI** if running:
   ```bash
   python3 scripts/restart_comfyui.py
   ```

4. **Verify model appears** in API:
   ```bash
   curl -s http://192.168.1.215:8188/object_info | python3 -c "
   import json, sys
   data = json.load(sys.stdin)
   ckpts = data.get('CheckpointLoaderSimple', {}).get('input', {}).get('required', {}).get('ckpt_name', [[]])[0]
   for c in ckpts: print(c)
   "
   ```

5. **Update lora_catalog.yaml** if it's a LoRA (see [LORA_CATALOG.md](LORA_CATALOG.md))

### Example: Adding a New LoRA

```bash
# 1. Download
ssh moira
cd C:\Users\jrjen\comfy\models\loras
curl -L https://civitai.com/api/download/models/12345 -o new_lora.safetensors

# 2. Restart ComfyUI
python C:\Users\jrjen\comfy-gen\scripts\restart_comfyui.py

# 3. Verify (from magneto)
curl -s http://192.168.1.215:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
loras = data.get('LoraLoader', {}).get('input', {}).get('required', {}).get('lora_name', [[]])[0]
print('new_lora.safetensors' in loras)
"

# 4. Update documentation
# - Add to MODEL_REGISTRY.md
# - Add to lora_catalog.yaml with tags and compatibility
```

---

## Compatibility Matrix

### Base Models and LoRAs

| LoRA | SD 1.5 | Wan 2.2 T2V High | Wan 2.2 T2V Low | Wan 2.2 I2V High | Wan 2.2 I2V Low |
|------|--------|------------------|-----------------|------------------|-----------------|
| **Acceleration LoRAs** | | | | | |
| wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise | ❌ | ✅ | ❌ | ❌ | ❌ |
| wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise | ❌ | ❌ | ✅ | ❌ | ❌ |
| wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise | ❌ | ❌ | ❌ | ✅ | ❌ |
| wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise | ❌ | ❌ | ❌ | ❌ | ✅ |
| Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Physics/Motion LoRAs** | | | | | |
| BoobPhysics_WAN_v6 | ❌ | ✅ | ✅ | ✅ | ✅ |
| BounceHighWan2_2 | ❌ | ✅ | ❌ | ✅ | ❌ |
| BounceLowWan2_2 | ❌ | ❌ | ✅ | ❌ | ✅ |
| wan-thiccum-v3 | ❌ | ✅ | ✅ | ✅ | ✅ |

**Legend:**
- ✅ Compatible and tested
- ❌ Not compatible
- ⚠️ Experimental/untested

### Workflow Compatibility

| Workflow | Primary Model | Required LoRAs | Input Image | Output Type |
|----------|---------------|----------------|-------------|-------------|
| flux-dev.json | v1-5-pruned-emaonly-fp16.safetensors | None | No | PNG (512x512) |
| sd15-img2img.json | v1-5-pruned-emaonly-fp16.safetensors | None | Yes | PNG (variable) |
| wan22-t2v.json | wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors | wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise | No | MP4 (848x480, 81 frames) |
| wan22-i2v.json | wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors | wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise | Yes | MP4 (848x480, 81 frames) |

---

## Model Performance

### Generation Times (Approximate)

| Model | Resolution | Steps | GPU | Time |
|-------|------------|-------|-----|------|
| SD 1.5 (flux-dev) | 512x512 | 20 | RTX 5090 | 10-15s |
| SD 1.5 (img2img) | 512x512 | 20 | RTX 5090 | 10-20s |
| Wan 2.2 T2V | 848x480 (81 frames) | 4 | RTX 5090 | 2-5 min |
| Wan 2.2 I2V | 848x480 (81 frames) | 4 | RTX 5090 | 2-5 min |

**Notes:**
- Times vary based on current GPU load and queue depth
- 4-step LoRAs reduce Wan 2.2 generation time significantly (from 15+ min to 2-5 min)
- Multiple concurrent generations will increase individual times

### VRAM Usage

| Model | VRAM Required | Notes |
|-------|---------------|-------|
| SD 1.5 | ~4 GB | Can run on most GPUs |
| Wan 2.2 (FP8) | ~12 GB | Requires high-end GPU |
| Wan 2.2 + LoRAs | ~14 GB | Additional overhead |

## Viewing Available Models via API

```bash
# List all checkpoints
curl -s http://192.168.1.215:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
ckpts = data.get('CheckpointLoaderSimple', {}).get('input', {}).get('required', {}).get('ckpt_name', [[]])[0]
for c in ckpts: print(c)
"
```

---

**Documentation Policy:** This is an authoritative reference document. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only.
