# Complete Model Inventory

This document provides a holistic view of all models, checkpoints, LoRAs, VAEs, diffusion models, and text encoders available on moira (192.168.1.215).

Last updated: January 4, 2026

## Quick Reference

| Category | Count | Total Size |
|----------|-------|------------|
| Checkpoints | 4 | ~15 GB |
| LoRAs | 56 | ~74 GB |
| VAEs | 4 | ~30 GB |
| Diffusion Models | 8 | ~61 GB |
| Text Encoders | 2 | ~12 GB |

## Checkpoints (Base Models)

| Filename | Architecture | Size | Best For |
|----------|--------------|------|----------|
| `ponyDiffusionV6XL_v6StartWithThisOne.safetensors` | Pony/SDXL | 6.9 GB | **NSFW (Best)**, artistic, anime |
| `realisticVisionV60B1_v51HyperVAE.safetensors` | SD 1.5 | 4.3 GB | Photorealistic portraits |
| `majicmixRealistic_v7.safetensors` | SD 1.5 | 2.1 GB | Photorealistic, Asian faces |
| `v1-5-pruned-emaonly-fp16.safetensors` | SD 1.5 | 2.1 GB | Base SD 1.5, general purpose |

### Workflow Mapping

| Checkpoint | Workflow File |
|------------|---------------|
| ponyDiffusionV6XL | `workflows/pony-v6.json` |
| realisticVisionV60B1 | `workflows/realistic-vision.json` |
| majicmixRealistic_v7 | `workflows/majicmix-realistic.json` |
| Flux.1 Dev | `workflows/flux-dev.json` |

## VAEs

| Filename | Architecture | Size | Notes |
|----------|--------------|------|-------|
| `sdxl_vae.safetensors` | SDXL/Pony | 335 MB | For SDXL-based models |
| `wan_2.1_vae.safetensors` | Wan 2.1/2.2 | 254 MB | For Wan video models |
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | Wan 2.2 | 14.3 GB | T2V model (also in VAE folder) |
| `wan22I2VA14BGGUF_a14bHigh.gguf` | Wan 2.2 | 15.4 GB | I2V GGUF model |

## Diffusion Models

| Filename | Purpose | Size |
|----------|---------|------|
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | Text-to-Video (high noise) | 14.3 GB |
| `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` | Text-to-Video (low noise) | 14.3 GB |
| `wan22I2VA14BGGUF_a14bHigh.gguf` | Image-to-Video | 15.4 GB |
| `cosmos_predict2_2B_video2world_480p_16fps.safetensors` | Video generation | 3.9 GB |
| `NSFW-22-H-e8.safetensors` | NSFW for high noise | 614 MB |
| `NSFW-22-L-e8.safetensors` | NSFW for low noise | 614 MB |

## Text Encoders

| Filename | Size | Used By |
|----------|------|---------|
| `oldt5_xxl_fp8_e4m3fn_scaled.safetensors` | 4.9 GB | Flux, general |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.7 GB | Wan 2.2, video |

---

## LoRAs by Category

### Image Generation - SD 1.5

| Filename | Size | Triggers | Strength | Purpose |
|----------|------|----------|----------|---------|
| `airoticart_penis.safetensors` | 144 MB | `penerec`, `penflac` | 0.85 | Male anatomy |
| `polyhedron_skin.safetensors` | 144 MB | `detailed skin`, `skin blemish` | 0.6 | Skin texture |
| `realora_skin.safetensors` | 144 MB | None | 0.6 | Subtle skin |
| `more_details.safetensors` | 9.5 MB | None | 0.5 | Detail enhancement |
| `add_detail.safetensors` | 38 MB | None | 0.4 | Detail tweaking |
| `PixelArtRedmond15V-PixelArt-PIXARFK.safetensors` | 27 MB | `pixel art` | 0.8 | Pixel art style |
| `vector_icons_game_assets.safetensors` | 170 MB | `vector icon` | 0.8 | Game icons |

### Image Generation - Flux.1

| Filename | Size | Triggers | Strength | Purpose |
|----------|------|----------|----------|---------|
| `nsfw_master_flux.safetensors` | 164 MB | None | 0.9 | Uncensors Flux |
| `Hyper-FLUX.1-dev-8steps-lora.safetensors` | 1.4 GB | None | 0.125 | 8-step acceleration |
| `realism_lora.safetensors` | 22 MB | None | 0.8 | Photorealism |
| `scenery_lora.safetensors` | 45 MB | None | 0.7 | Landscapes |
| `mjv6_lora.safetensors` | 45 MB | None | 0.8 | Midjourney style |
| `art_lora.safetensors` | 359 MB | None | 0.7 | Artistic |
| `anime_lora.safetensors` | 45 MB | None | 0.8 | Anime style |
| `disney_lora.safetensors` | 45 MB | None | 0.8 | Disney/Pixar |
| `GothicPixelArtV1.1.safetensors` | 228 MB | `gothic pixel art` | 0.8 | Gothic pixel style |

### Image Generation - Pony/SDXL

| Filename | Size | Triggers | Strength | Purpose |
|----------|------|----------|----------|---------|
| `ruined_orgasm_pony.safetensors` | 55 MB | `pov, penis, cum, projectile cum, twitching penis` | 0.8 | Ruined orgasm concept |

### Video Generation - Wan 2.2 Acceleration

| Filename | Size | Compatible Model | Strength |
|----------|------|------------------|----------|
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` | 1.2 GB | T2V High Noise | 1.0 |
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors` | 1.2 GB | T2V Low Noise | 1.0 |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | 1.2 GB | I2V High Noise | 1.0 |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | 1.2 GB | I2V Low Noise | 1.0 |
| `Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors` | 1.2 GB | I2V High Noise | 1.0 |

### Video Generation - Wan 2.2 Physics/Motion

| Filename | Size | Strength | Purpose |
|----------|------|----------|---------|
| `BoobPhysics_WAN_v6.safetensors` | 38 MB | 0.7 | Body physics |
| `BounceHighWan2_2.safetensors` | 307 MB | 0.7 | Bounce (high noise) |
| `BounceLowWan2_2.safetensors` | 307 MB | 0.7 | Bounce (low noise) |
| `wan-thiccum-v3.safetensors` | 307 MB | 0.7 | Body enhancement |

### Video Generation - Wan 2.2 NSFW

| Filename | Size | Type | Noise Level |
|----------|------|------|-------------|
| `NSFW-22-H-e8.safetensors` | 614 MB | General NSFW | High |
| `NSFW-22-L-e8.safetensors` | 614 MB | General NSFW | Low |
| `wan2.2-i2v-high-pov-insertion-v1.0.safetensors` | 307 MB | POV insertion | High |
| `wan2.2-i2v-low-pov-insertion-v1.0.safetensors` | 307 MB | POV insertion | Low |
| `wan2.2-i2v-high-oral-insertion-v1.0.safetensors` | 307 MB | Oral | High |
| `wan2.2-i2v-low-oral-insertion-v1.0.safetensors` | 307 MB | Oral | Low |
| `wan2.2-i2v-high-cumshot-v1.0.safetensors` | 307 MB | Cumshot | High |
| `wan2.2-i2v-low-cumshot-v1.0.safetensors` | 307 MB | Cumshot | Low |
| `WAN-2.2-I2V-HandjobBlowjobCombo-HIGH-v1.safetensors` | 614 MB | Handjob/Blowjob | High |
| `WAN-2.2-I2V-HandjobBlowjobCombo-LOW-v1.safetensors` | 614 MB | Handjob/Blowjob | Low |
| `Wan2.2 - T2V - POV Hand Job - HIGH 14B.safetensors` | 307 MB | POV Handjob | High |
| `Wan2.2 - T2V - POV Hand Job - LOW 14B.safetensors` | 307 MB | POV Handjob | Low |
| `Wan2.2 - T2V - Facial - LOW 14B.safetensors` | 614 MB | Facial | Low |
| `Wan2.2 v2 - T2V - Body Shots - LOW 14B.safetensors` | 307 MB | Body shots | Low |
| `wan22-f4c3spl4sh-100epoc-high-k3nk.safetensors` | 319 MB | Facial splash | High |
| `wan22-f4c3spl4sh-154epoc-low-k3nk.safetensors` | 307 MB | Facial splash | Low |
| `wan22-ultimatedeepthroat-I2V-101epoc-low-k3nk.safetensors` | 307 MB | Deepthroat | Low |
| `wan_cumshot.safetensors` | 307 MB | Cumshot | Both |
| `WAN_dr34mj0b.safetensors` | 180 MB | Dreamjob | Both |
| `wan2.2-rapid-mega-aio-v1.safetensors` | 24.3 GB | All-in-one | Both |
| `doggyPOV_v1_1.safetensors` | 539 MB | Doggy POV | Both |
| `BetterTitfuck_v4_July2025.safetensors` | 153 MB | Titfuck | Both |

### Legacy/Large Anatomy LoRAs (Wan 2.2 - NOT for SD 1.5)

⚠️ **WARNING**: These are ~307MB and designed for Wan 2.2 video, NOT SD 1.5 images!

| Filename | Size | Notes |
|----------|------|-------|
| `big_breasts_v2_epoch_30.safetensors` | 307 MB | Video only |
| `deepthroat_epoch_80.safetensors` | 307 MB | Video only |
| `dicks_epoch_100.safetensors` | 307 MB | Video only |
| `erect_penis_epoch_80.safetensors` | 307 MB | Video only |
| `flaccid_penis_epoch_100.safetensors` | 307 MB | Video only |

---

## Architecture Quick Reference

### SD 1.5 Image Generation
- **Checkpoints**: realisticVision, majicMIX, v1-5-pruned
- **LoRA Size**: 9-150 MB typically
- **LoRAs**: airoticart_penis, polyhedron_skin, realora_skin, more_details, add_detail

### SDXL/Pony Image Generation
- **Checkpoints**: ponyDiffusionV6XL
- **LoRA Size**: 55-400 MB typically  
- **LoRAs**: ruined_orgasm_pony
- **Notes**: Pony is excellent for NSFW without needing anatomy LoRAs

### Flux.1 Image Generation
- **Checkpoints**: Uses flux1-dev-fp8 (not on disk, loaded dynamically)
- **LoRA Size**: 22 MB - 1.4 GB
- **LoRAs**: nsfw_master_flux (required for NSFW), Hyper-FLUX (acceleration)
- **Notes**: Censored by default, needs nsfw_master_flux LoRA

### Wan 2.2 Video Generation
- **Diffusion Models**: wan2.2_t2v_high/low_noise, wan22I2V
- **LoRA Size**: 300-600 MB typically (much larger than image LoRAs)
- **LoRAs**: Many NSFW-specific ones, physics, acceleration
- **Notes**: High noise = more artistic, Low noise = more realistic

---

## Recommended Stacks

### Male NSFW (Best Results - Pony)
```bash
--workflow workflows/pony-v6.json
# No LoRA needed, Pony handles NSFW natively
# Use score_9, score_8_up prefixes
```

### Male NSFW (SD 1.5 Alternative)
```bash
--workflow workflows/realistic-vision.json
--lora "airoticart_penis.safetensors:0.85"
--lora "realora_skin.safetensors:0.5"
# Triggers: penerec/penflac
```

### Fellatio/Oral (Pony)
```bash
--workflow workflows/pony-v6.json
# score_9, blowjob, fellatio, oral sex, large erect penis
```

### Ruined Orgasm (Pony)
```bash
--workflow workflows/pony-v6.json
--lora "ruined_orgasm_pony.safetensors:0.8"
# Triggers: pov, penis, cum, projectile cum, twitching penis, orgasm
```

### Facial/Cumshot (Pony)
```bash
--workflow workflows/pony-v6.json
# cum on face, facial cumshot, semen dripping
```

### Flux NSFW
```bash
--workflow workflows/flux-dev.json
--lora "nsfw_master_flux.safetensors:0.9"
# Must use this LoRA or Flux will censor
```

---

## Storage Locations on moira

```
C:\Users\jrjen\comfy\models\
├── checkpoints/      # Base models (~15 GB)
├── loras/            # LoRA adapters (~74 GB)
├── vae/              # VAE models (~30 GB)
├── diffusion_models/ # Wan 2.2, Cosmos (~61 GB)
├── text_encoders/    # T5, UMT5 (~12 GB)
└── unet/             # UNet models (~1 GB)
```

Total model storage: ~193 GB
