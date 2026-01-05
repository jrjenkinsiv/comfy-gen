# NSFW Generation Learnings

> Accumulated knowledge from testing photorealistic NSFW image generation.
> This document captures failure modes, solutions, and best practices.

## Current Date: January 4, 2026

---

## Model Selection

### For Photorealistic Asian Women

| Model | Type | Strengths | Weaknesses |
|-------|------|-----------|------------|
| **MajicMix Realistic v7** | SD 1.5 | Realistic skin, good lighting | Creates duplicate people, ignores "solo" |
| Pony V6 | Flux-based | Good anatomy | Too anime/stylized, faces look same |
| Realistic Vision | SD 1.5 | Western faces | Less accurate for Asian features |

**Current Best**: MajicMix Realistic v7 with `polyhedron_skin` LoRA

### Key LoRAs for Realism

| LoRA | Trigger Words | Strength | Purpose |
|------|---------------|----------|---------|
| `polyhedron_skin.safetensors` | `detailed skin`, `skin pores` | 0.5-0.7 | Realistic skin texture |
| `add_detail.safetensors` | `detailed` | 0.3-0.5 | General detail enhancement |

---

## Known Failure Modes

### 1. Duplicate/Merged People Problem

**Symptom**: Model generates 2+ people stacked or merged despite "solo" prompts.

**What DOESN'T work**:
- ❌ Adding "solo", "one person only", "single person" to positive prompt
- ❌ Adding "two people, multiple people, crowd" to negative prompt
- ❌ Portrait orientation (1024x1536)
- ❌ Higher CFG (tested up to 10)
- ❌ Fixed seeds

**Root Cause**: SD 1.5 models trained on datasets with many multi-person images. The model's latent space naturally tends toward generating multiple figures, especially at certain resolutions.

**Potential Solutions** (untested):
- Try different aspect ratios (extreme portrait like 768x1344)
- Use inpainting workflow to mask and regenerate faces
- Try regional prompting (different prompts for different image regions)
- Use ControlNet with single-person pose reference
- Try different models (e.g., ChilloutMix, BeautifulRealistic)

### 2. Anatomy Issues

**Symptom**: Detached limbs, extra appendages, merged body parts.

**What helps**:
- ✅ Upper body only (avoid full body shots)
- ✅ Heavy anatomy negatives: "detached limbs, floating limbs, disconnected body parts, extra limbs"
- ✅ Higher steps (80+)

**What doesn't help**:
- ❌ Explicit anatomy descriptions in prompt
- ❌ "Anatomically correct" in prompt

### 3. Prompt Adherence

**Symptom**: Model ignores specific requests (hair length, background, framing).

**Observations**:
- "White background" → Gets studio/bedroom instead
- "Shoulder length hair" → Gets very long hair
- "Upper body only" → Gets more of body

**Root Cause**: Aesthetic training overrides literal prompt interpretation.

---

## Validation System Limitations

### How CLIP Validation Works

```
Image → CLIP Image Encoder → Image Embedding
Prompt → CLIP Text Encoder → Text Embedding
Score = cosine_similarity(Image Embedding, Text Embedding)
```

**Score Range**: 0.0 to 1.0 (after transformation from -1 to 1)
- 0.60-0.70: Typical "passing" range
- 0.25: Current threshold (very lenient)

### What CLIP CAN Detect

- ✅ General semantic match (is this a woman? is she nude?)
- ✅ Major concept presence (beach, bedroom, studio)
- ✅ Obvious mismatches (prompt says car, image shows cat)

### What CLIP CANNOT Detect

- ❌ **Person count** - "solo woman" vs "two women" score similarly if both are women
- ❌ **Anatomy correctness** - Detached limbs still match "woman" concept
- ❌ **Specific details** - Hair length, exact pose, background specifics
- ❌ **Quality issues** - Blurry, artifacts, low resolution
- ❌ **Merged bodies** - Still matches "woman" keyword

### Why Low Scores Pass

Current threshold is 0.25 which is very lenient. A score of 0.647 means:
- Image somewhat matches prompt semantically
- Does NOT mean image is good or anatomically correct

### Improving Validation (Future Work)

1. **Add person count detection** - Use object detection (YOLO) to count humans
2. **Add quality metrics** - BRISQUE, NIQE for technical quality
3. **Add pose estimation** - OpenPose to verify single coherent skeleton
4. **ImageReward model** - Trained on human preferences, better than CLIP

---

## Generation Parameters

### DO NOT Specify Seed

**Problem**: Fixed seeds create deterministic outputs, preventing variety exploration.

```bash
# BAD - same seed = same patterns
--seed 2004

# GOOD - let it be random
# (don't specify --seed at all, or use --seed -1)
```

The batch script should use `random.randint()` for each generation.

### Recommended Parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| Steps | 80 | Quality balance |
| CFG | 7-8 | Higher = stricter but can cause artifacts |
| Sampler | dpmpp_sde | Good for photorealism |
| Scheduler | karras | Smooth progression |
| Width | 1024-1280 | Good detail |
| Height | 1024-1536 | Portrait for single person |

---

## Asian Ethnicity Variations

For testing diversity across Asian nationalities:

| Ethnicity | Key Visual Markers |
|-----------|-------------------|
| Vietnamese | Golden tan skin, almond eyes |
| Korean | Fair skin, double eyelids, v-line jaw |
| Japanese | Fair to medium skin, varied features |
| Thai | Golden/tan skin, softer features |
| Filipino | Medium tan skin, varied features |
| Chinese | Varied (north: fair, south: tan) |
| Indonesian | Medium tan skin, diverse features |
| Malaysian | Medium skin, Malay features |
| Taiwanese | Similar to southern Chinese |
| Singaporean | Mix of Chinese/Malay/Indian influences |

**Prompt Pattern**: 
```
beautiful [ethnicity] woman age [20-35], [skin tone] skin, [hair description]
```

---

## Best Practices Summary

1. **Don't trust "solo" prompts** - Model ignores them
2. **Don't specify seed** - Prevents exploration
3. **Use upper body framing** - Avoids leg anatomy issues
4. **Don't rely on CLIP validation** - Can't detect person count or anatomy
5. **Test many variations** - Different seeds, prompts, settings
6. **Visual review is required** - Automation can't catch key failures

---

## Future Improvements Needed

1. **Person Count Detection** - YOLO or similar to verify single person
2. **Pose Estimation** - OpenPose to verify coherent skeleton
3. **Face Detection** - Verify exactly one face in frame
4. **Stricter Validation Threshold** - Current 0.25 is too lenient
5. **Alternative Models** - Test ChilloutMix, BeautifulRealistic, etc.
6. **ControlNet Integration** - Use pose reference to enforce single person

---

## Session Log

### January 4, 2026

**Issue**: Generated 30+ images, all had duplicate people or anatomy issues.

**Attempted Fixes**:
1. Switched from Pony V6 to MajicMix Realistic ✅ (more realistic)
2. Added polyhedron_skin LoRA ✅ (better skin texture)
3. Added heavy anti-duplicate negatives ❌ (didn't help)
4. Portrait orientation (1024x1536) ❌ (didn't help)
5. CFG increased to 10 ❌ (didn't help)
6. Upper body framing ❌ (still got merged bodies)

**Conclusion**: SD 1.5 models fundamentally struggle with single-person constraint. Need either:
- Different model architecture
- ControlNet with pose reference
- Post-processing with inpainting
