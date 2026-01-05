# NSFW Generation Experiment Log

> Living document tracking observations from NSFW image generation testing.
> Updated as we learn. Observations, not conclusions.

---

## Models Tested

| Model | Type | Observations | Date |
|-------|------|--------------|------|
| MajicMix Realistic v7 | SD 1.5 | Realistic skin/lighting. Saw duplicate people issue in some tests. | 2026-01-04 |
| Pony V6 | SDXL-based | More stylized/anime look. Consistent faces across images. | 2026-01-04 |

*More models to test: ChilloutMix, BeautifulRealistic, Realistic Vision, etc.*

## LoRAs Tested

| LoRA | Trigger Words | Strength Tested | Observations | Date |
|------|---------------|-----------------|--------------|------|
| polyhedron_skin | `detailed skin`, `skin pores` | 0.5-0.7 | Adds skin texture detail | 2026-01-04 |
| add_detail | `detailed` | 0.3-0.5 | General detail boost | 2026-01-04 |

---

## Observations (Living Section)

### January 4, 2026 - Session 1

**What we tried:**
- MajicMix Realistic v7 with polyhedron_skin LoRA
- Various resolutions: 1280x1280, 1024x1536
- CFG values: 7.5, 8, 9, 10
- Heavy anti-duplicate negative prompts

**What we observed:**
- Some images showed two people merged/stacked despite "solo" in prompt
- Negative prompts for "two people, multiple people" did not prevent this
- Higher CFG (up to 10) did not prevent duplicate people
- Portrait orientation (1024x1536) did not prevent duplicate people
- CLIP validation scores (0.6-0.7) passed even for problematic images

**Open questions:**
- Is this specific to MajicMix or common across SD 1.5 models?
- Would ControlNet with pose reference help?
- Would different aspect ratios help?
- Need to test more models to compare

**NOT concluded yet:**
- We have NOT determined that SD 1.5 "fundamentally struggles" with single-person
- We have NOT determined that upper body framing is required
- We have NOT determined best model/LoRA combination
- More testing needed across models, LoRAs, settings

---

## Validation System Notes

### How CLIP Validation Works

```
Image -> CLIP Image Encoder -> Image Embedding
Prompt -> CLIP Text Encoder -> Text Embedding
Score = cosine_similarity(Image Embedding, Text Embedding)
```

**Current threshold:** 0.25 (lenient)
**Typical passing scores:** 0.60-0.70

### Observed Limitations

CLIP measures semantic similarity, not:
- Person count (one vs two people)
- Anatomy correctness
- Specific detail adherence (hair length, exact pose)
- Image quality (blur, artifacts)

**Implication:** Visual review still required. CLIP validation is a filter, not a guarantee.

---

## Parameter Notes

### Seed

For exploration/batch testing, avoid specifying fixed seeds - this limits variety.
For reproducibility (demonstrating a specific result), seeds are useful.

### Resolution

Testing various:
- 1280x1280 (square)
- 1024x1536 (portrait)
- 768x1152 (smaller portrait)
- More to test

### CFG

Tested range: 6.0 - 10.0
Higher values = stricter prompt adherence but can introduce artifacts.

---

## Batch Testing In Progress

Running batch_asian_nsfw.py with:
- 10 Asian ethnicities
- Random seeds (no fixed seeds)
- Varied LoRAs, CFG, steps, resolutions
- Multiple models

Results will inform future observations.

---

## Future Experiment Ideas

*To be converted to GitHub issues:*

1. Add person count detection (YOLO or similar)
2. Add pose estimation validation (OpenPose)
3. Test ControlNet for pose enforcement
4. Test more realistic models (ChilloutMix, etc.)
5. Test regional prompting
6. Adjust validation threshold
7. Add quality metrics (BRISQUE, NIQE)

---

## Git Commit References

All changes should be tracked via git commits. This doc supplements git history
with higher-level observations that span multiple commits/sessions.
