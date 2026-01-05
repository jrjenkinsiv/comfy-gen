# LoRA Reference Guide

This document tracks all LoRAs, their trigger words, compatible architectures, and recommended settings.

## Quick Reference

| LoRA | Architecture | Trigger Words | Strength | Downloads |
|------|--------------|---------------|----------|-----------|
| airoticart_penis | SD 1.5 | `penerec` (erect), `penflac` (flaccid) | 0.8-0.85 | 21K |
| polyhedron_skin | SD 1.5 | `detailed skin`, `skin blemish`, `skin pores` | 0.5-0.7 | 72K |
| realora_skin | SD 1.5 | None (style transfer) | 0.5-0.7 | 45K |
| nsfw_master_flux | Flux.1 D | None (NSFW enabling) | 0.7-1.0 | 113K |

## Detailed LoRA Documentation

### airoticart_penis.safetensors
- **Source**: CivitAI ID 15040
- **Architecture**: SD 1.5
- **Size**: 144 MB
- **Purpose**: Realistic male genitalia
- **Trigger Words**:
  - `penerec` - Erect penis
  - `penflac` - Flaccid penis
  - `erect penis` - Alternative trigger
  - `flaccid penis` - Alternative trigger
- **Recommended Strength**: 0.8-0.85
- **Tips**: 
  - Add opposite trigger to negative prompt (e.g., `penflac` in negative when wanting erect)
  - Combine with skin LoRAs for better results

### polyhedron_skin.safetensors
- **Source**: CivitAI ID 109043
- **Architecture**: SD 1.5
- **Size**: 144 MB
- **Purpose**: Realistic skin texture (works for male and female)
- **Trigger Words**:
  - `detailed skin` - Enables detailed skin texture
  - `skin blemish` - Adds realistic imperfections
  - `skin pores` - Emphasizes pore detail
- **Recommended Strength**: 0.5-0.7
- **Tips**: Stack with anatomy LoRAs for best results

### realora_skin.safetensors
- **Source**: CivitAI ID 137258
- **Architecture**: SD 1.5
- **Size**: 144 MB
- **Purpose**: Realistic skin texture, more subtle than polyhedron
- **Trigger Words**: None required (style transfer)
- **Recommended Strength**: 0.5-0.7
- **Tips**: Good for photorealistic portraits

### nsfw_master_flux.safetensors
- **Source**: CivitAI ID 667086
- **Architecture**: Flux.1 D
- **Size**: 164 MB
- **Purpose**: Enables NSFW content generation on Flux models
- **Trigger Words**: None required
- **Recommended Strength**: 0.7-1.0
- **Tips**: 
  - Flux models are censored by default, this LoRA unlocks NSFW
  - Higher strength = more explicit content

## Wan 2.2 Video LoRAs (NOT for images)

These are for video generation only - they are ~300MB and designed for Wan 2.2:

| LoRA | Purpose | Size |
|------|---------|------|
| erect_penis_epoch_80 | Erect penis in video | 307 MB |
| flaccid_penis_epoch_100 | Flaccid penis in video | 307 MB |
| dicks_epoch_100 | General penis in video | 307 MB |
| big_breasts_v2_epoch_30 | Breasts in video | 307 MB |

**WARNING**: Do not use Wan 2.2 LoRAs with SD 1.5/SDXL/Pony - they are incompatible.

## Architecture Compatibility

| Architecture | LoRA Size Range | Compatible Checkpoints |
|--------------|-----------------|------------------------|
| SD 1.5 | 9-150 MB | realisticVision, majicMIX, v1-5-pruned |
| SDXL 1.0 | 200-900 MB | SDXL base |
| Pony Diffusion V6 | 200-400 MB | ponyDiffusionV6XL |
| Flux.1 D | 150-700 MB | Flux.1 Dev |
| Wan 2.2 | 300-400 MB | Wan 2.2 video models |

## Pony Diffusion V6 Score System

Pony V6 was trained with a quality rating system. **Always include score prefixes** in your prompts:

### Quality Score Tags (Required Prefix)
```
score_9           - Highest quality (top ~10%)
score_8_up        - High quality and above
score_7_up        - Good quality and above
score_6_up        - Acceptable quality and above
score_5_up        - Average and above
score_4_up        - Below average and above
```

### Recommended Positive Prefix
```
score_9, score_8_up, score_7_up, [your detailed prompt here]
```

### Recommended Negative Prefix
```
score_6, score_5, score_4, [your detailed negative prompt here]
```

### How It Works
- The model was trained with human-rated quality scores
- Including high scores in positive tells model "generate like the best examples"
- Including low scores in negative avoids low-quality outputs
- **This is additive** - you STILL need detailed prompts after the score prefix!

### Example (Correct):
```
Positive: score_9, score_8_up, score_7_up, beautiful young asian woman with 
long black hair, kneeling on a luxurious bed with silk sheets, POV blowjob, 
penis in mouth, looking up at viewer seductively with half-lidded eyes, 
soft bedroom lighting from a bedside lamp creating warm golden highlights, 
realistic skin texture with subtle shine, intimate atmosphere...

Negative: score_6, score_5, score_4, deformed, ugly, bad anatomy, blurry, 
extra limbs, missing fingers, low quality, watermark, text, cartoon, anime
```

### Example (WRONG - too simple):
```
Positive: score_9, score_8_up, score_7_up, asian woman blowjob
```

**Key Insight**: Score tags tell the model QUALITY level, not CONTENT. You still need rich, detailed descriptions for good results.

## Prompt Engineering Tips

### Male Anatomy
```
Positive: penerec, large erect penis, circumcised/uncircumcised, realistic male genitalia, 
          testicles visible, anatomically correct, detailed skin
Negative: female, woman, vagina, vulva, breasts, feminine, penflac, flaccid, 
          deformed genitals, multiple penises
```

### Fellatio/Oral Scenes
```
Positive: fellatio, oral sex, blowjob, sucking, mouth, pov, female pov, 
          detailed face, realistic
Negative: teeth visible, biting, cartoon, anime, deformed face, 
          multiple people (if solo desired)
```

### Realistic Skin
```
Positive: detailed skin, skin pores, skin blemish, raw photo, photorealistic,
          natural lighting, subsurface scattering
Negative: plastic skin, airbrushed, smooth skin, cartoon, anime, CGI
```

## Stacking LoRAs

For best results, stack complementary LoRAs:

### Male Photorealistic Stack
```bash
--lora "airoticart_penis.safetensors:0.85" \
--lora "polyhedron_skin.safetensors:0.6"
```

### SD 1.5 Skin Stack
```bash
--lora "realora_skin.safetensors:0.6" \
--lora "polyhedron_skin.safetensors:0.4"
```

## Seed Behavior

- **Omit `--seed`**: ComfyUI generates a random seed (recommended for variety)
- **`--seed -1`**: Explicitly request random seed
- **`--seed N`**: Fixed seed for reproducibility

**When to use fixed seeds:**
- A/B testing different prompts with same composition
- Iterating on a specific image
- Documenting reproducible results

**When to use random seeds:**
- Batch generation for variety
- Exploring prompt space
- Production content generation

## Adding New LoRAs

When adding a new LoRA, document:

1. **Source**: CivitAI/HuggingFace ID and URL
2. **Architecture**: Which base model(s) it's trained for
3. **Size**: File size (helps identify architecture)
4. **Trigger Words**: Required activation phrases
5. **Strength**: Recommended range
6. **Tips**: Any usage notes or gotchas
