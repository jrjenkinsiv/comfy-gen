# LoRA Catalog

This catalog provides semantic descriptions and metadata for all LoRAs available on moira. It is used by the intelligent model selection system to automatically choose appropriate LoRAs based on prompt analysis.

**Last Updated:** 2026-01-04  
**Location:** `C:\Users\jrjen\comfy\models\loras\`

## Format

Each LoRA entry includes:
- **Filename:** Exact filename as stored on disk
- **Tags:** Semantic keywords for matching
- **Compatible With:** Which models this LoRA works with
- **Recommended Strength:** Suggested strength_model/strength_clip values
- **Description:** What the LoRA does and when to use it

---

## Acceleration LoRAs

These LoRAs reduce the number of sampling steps required, speeding up generation time.

### wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors

- **Tags:** acceleration, speed, 4-step, fast, quick, text-to-video
- **Compatible With:** wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors
- **Recommended Strength:** 1.0 (model), 1.0 (clip)
- **Description:** Reduces Wan 2.2 text-to-video generation to just 4 sampling steps (from default 50). Use when speed is critical and quality tradeoff is acceptable. Works only with high noise variant.

### wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors

- **Tags:** acceleration, speed, 4-step, fast, quick, text-to-video
- **Compatible With:** wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength:** 1.0 (model), 1.0 (clip)
- **Description:** Reduces Wan 2.2 text-to-video generation to just 4 sampling steps (from default 50). Use when speed is critical and quality tradeoff is acceptable. Works only with low noise variant.

### wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors

- **Tags:** acceleration, speed, 4-step, fast, quick, image-to-video
- **Compatible With:** wan2.2_i2v_high_noise (not currently in registry)
- **Recommended Strength:** 1.0 (model), 1.0 (clip)
- **Description:** Reduces Wan 2.2 image-to-video generation to just 4 sampling steps. Use for fast I2V generation with high noise model.

### wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors

- **Tags:** acceleration, speed, 4-step, fast, quick, image-to-video
- **Compatible With:** wan2.2_i2v_low_noise (not currently in registry)
- **Recommended Strength:** 1.0 (model), 1.0 (clip)
- **Description:** Reduces Wan 2.2 image-to-video generation to just 4 sampling steps. Use for fast I2V generation with low noise model.

### Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors

- **Tags:** acceleration, speed, 4-step, fast, seko, image-to-video
- **Compatible With:** wan2.2_i2v_high_noise (not currently in registry)
- **Recommended Strength:** 1.0 (model), 1.0 (clip)
- **Description:** Alternative 4-step acceleration for Wan 2.2 I2V using Seko training method. May produce different results than standard lightx2v.

---

## Physics & Motion LoRAs

These LoRAs enhance realism and dynamics in video generation.

### BoobPhysics_WAN_v6.safetensors

- **Tags:** physics, motion, body, realistic, dynamics, bounce
- **Compatible With:** wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors, wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength:** 0.7 (model), 0.7 (clip)
- **Description:** Enhances realistic body physics and movement in video generation. Use when generating videos with dynamic body motion or natural movement.

### BounceHighWan2_2.safetensors

- **Tags:** motion, bounce, dynamics, movement, high-energy
- **Compatible With:** wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors
- **Recommended Strength:** 0.7 (model), 0.7 (clip)
- **Description:** Adds enhanced bounce and motion dynamics to video. Works with high noise variant. Use for energetic, dynamic scenes with significant movement.

### BounceLowWan2_2.safetensors

- **Tags:** motion, bounce, dynamics, movement, subtle
- **Compatible With:** wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength:** 0.7 (model), 0.7 (clip)
- **Description:** Adds enhanced bounce and motion dynamics to video. Works with low noise variant. Use for subtle, natural movement enhancement.

### wan-thiccum-v3.safetensors

- **Tags:** body, enhancement, curves, proportions
- **Compatible With:** wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors, wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength:** 0.6 (model), 0.6 (clip)
- **Description:** Body proportion enhancement for character generation. Use when generating characters with enhanced physical features.

---

## Selection Guidelines

### By Use Case

| Use Case | Suggested LoRAs |
|----------|----------------|
| Fast video generation | 4-step acceleration LoRAs |
| Realistic motion/physics | Physics/motion LoRAs |
| Dynamic action scenes | Bounce LoRAs + Physics LoRAs |
| Character-focused video | Body enhancement + Physics LoRAs |

### Combining LoRAs

Multiple LoRAs can be chained together. Common combinations:

1. **Fast + Realistic Motion**
   - Acceleration LoRA (strength 1.0) + Physics LoRA (strength 0.7)
   - Example: Fast generation with realistic movement

2. **Maximum Quality Motion**
   - Physics LoRA (strength 0.7) + Bounce LoRA (strength 0.6)
   - Example: Slow but highly realistic dynamic scenes

### Strength Recommendations

| Strength Range | When to Use |
|----------------|-------------|
| 0.3 - 0.5 | Subtle effect, blending with base model |
| 0.6 - 0.8 | Standard use, balanced enhancement |
| 0.9 - 1.0 | Maximum effect, may override base model |
| 1.0+ | Not recommended (may cause artifacts) |

**Note:** Acceleration LoRAs should always use strength 1.0 as they fundamentally alter the sampling process.

---

## API Query

To get real-time list of available LoRAs:

```bash
curl -s http://192.168.1.215:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
loras = data.get('LoraLoader', {}).get('input', {}).get('required', {}).get('lora_name', [[]])[0]
for lora in loras:
    print(lora)
"
```

This catalog should be kept in sync with actual installed LoRAs on moira.
