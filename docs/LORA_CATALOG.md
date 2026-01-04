# LoRA Catalog

This catalog provides semantic descriptions of all available LoRAs to enable intelligent selection based on prompt analysis.

## Format

Each LoRA entry includes:
- **Filename**: Exact filename in `models/loras/`
- **Tags**: Semantic keywords for matching
- **Compatible With**: Base models this LoRA works with
- **Recommended Strength**: Default strength value (0.0-1.0+)
- **Description**: What the LoRA does and when to use it

---

## Acceleration LoRAs

These LoRAs reduce the number of inference steps required, speeding up generation.

### wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors

- **Tags**: acceleration, speed, 4-step, fast, quick, text-to-video
- **Compatible With**: wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 1.0 (model), 1.0 (clip)
- **Description**: Reduces Wan 2.2 text-to-video generation to 4 steps (from 50). Use when speed is critical. Works only with high noise variant.

### wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors

- **Tags**: acceleration, speed, 4-step, fast, quick, text-to-video
- **Compatible With**: wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 1.0 (model), 1.0 (clip)
- **Description**: Reduces Wan 2.2 text-to-video generation to 4 steps (from 50). Use when speed is critical. Works only with low noise variant.

### wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors

- **Tags**: acceleration, speed, 4-step, fast, quick, image-to-video, animation
- **Compatible With**: wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 1.0 (model), 1.0 (clip)
- **Description**: Reduces Wan 2.2 image-to-video generation to 4 steps. Use for fast image animation. Works only with high noise I2V variant.

### wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors

- **Tags**: acceleration, speed, 4-step, fast, quick, image-to-video, animation
- **Compatible With**: wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 1.0 (model), 1.0 (clip)
- **Description**: Reduces Wan 2.2 image-to-video generation to 4 steps. Use for fast image animation. Works only with low noise I2V variant.

### Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors

- **Tags**: acceleration, speed, 4-step, fast, quick, image-to-video, seko
- **Compatible With**: wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 1.0 (model), 1.0 (clip)
- **Description**: Alternative 4-step acceleration LoRA for Wan 2.2 I2V by Seko. May have different quality characteristics than lightx2v variant.

---

## Physics & Motion LoRAs

These LoRAs enhance realistic motion, physics simulation, and body dynamics in video generation.

### BoobPhysics_WAN_v6.safetensors

- **Tags**: physics, motion, body, realistic, bounce, movement, anatomy
- **Compatible With**: wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors, wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 0.7 (model), 0.7 (clip)
- **Description**: Enhances realistic body physics and movement dynamics in video. Use for natural motion simulation with anatomically correct physics.

### BounceHighWan2_2.safetensors

- **Tags**: bounce, motion, physics, movement, dynamic, high-noise
- **Compatible With**: wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors, wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 0.7 (model), 0.7 (clip)
- **Description**: Enhances bouncing and dynamic motion in high noise Wan 2.2 models. Use when generating content with significant motion or movement.

### BounceLowWan2_2.safetensors

- **Tags**: bounce, motion, physics, movement, dynamic, low-noise
- **Compatible With**: wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors, wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 0.7 (model), 0.7 (clip)
- **Description**: Enhances bouncing and dynamic motion in low noise Wan 2.2 models. Use when generating content with significant motion or movement.

### wan-thiccum-v3.safetensors

- **Tags**: body, enhancement, figure, shape, anatomy
- **Compatible With**: wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors, wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
- **Recommended Strength**: 0.7 (model), 0.7 (clip)
- **Description**: Body enhancement LoRA for Wan 2.2 video generation. Modifies figure proportions and body shapes.

---

## Selection Guidelines

### When to Use Acceleration LoRAs

- **Always recommended** for faster generation unless maximum quality is critical
- Use strength 1.0 for both model and clip
- Must match noise level (high/low) with base model
- Reduces generation time by ~90% (50 steps → 4 steps)

### When to Use Physics/Motion LoRAs

- Prompts mentioning: movement, walking, running, dancing, bouncing, motion
- Prompts with active subjects: "person walking", "car driving", "ball bouncing"
- Use strength 0.6-0.8 depending on desired effect intensity
- Can be combined with acceleration LoRAs

### Strength Recommendations

| Strength | Effect | Use Case |
|----------|--------|----------|
| 0.3-0.5 | Subtle | Light influence, preserving original style |
| 0.6-0.8 | Moderate | Balanced effect, recommended for most cases |
| 0.9-1.0 | Strong | Maximum effect, required for acceleration LoRAs |
| 1.0+ | Very Strong | May cause artifacts, use with caution |

### Compatibility Matrix

| Base Model | Acceleration LoRA | Physics LoRA |
|-----------|------------------|--------------|
| wan2.2_t2v_high_noise | lightx2v_4steps_v1.1_high_noise | BounceHighWan2_2, BoobPhysics_WAN_v6 |
| wan2.2_t2v_low_noise | lightx2v_4steps_v1.1_low_noise | BounceLowWan2_2, BoobPhysics_WAN_v6 |
| wan2.2_i2v_high_noise | lightx2v_4steps_v1_high_noise, Seko-V1 | BounceHighWan2_2 |
| wan2.2_i2v_low_noise | lightx2v_4steps_v1_low_noise | BounceLowWan2_2 |
| v1-5-pruned-emaonly-fp16 | None | None |

---

## Examples

### Fast Text-to-Video
**Prompt**: "a car driving down a highway"
**Selection**: wan2.2_t2v_high_noise + lightx2v_4steps_v1.1_high_noise (1.0)

### Motion-Heavy Video
**Prompt**: "a person dancing energetically"
**Selection**: wan2.2_t2v_high_noise + lightx2v_4steps_v1.1_high_noise (1.0) + BounceHighWan2_2 (0.7)

### Quality-Focused Image
**Prompt**: "a photorealistic portrait"
**Selection**: v1-5-pruned-emaonly-fp16 (no LoRAs)

### Fast Image Animation
**Prompt**: "the person starts walking forward"
**Selection**: wan2.2_i2v_high_noise + lightx2v_4steps_v1_high_noise (1.0)
