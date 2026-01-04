# Quality System Design

> Design document for ComfyGen's image quality assessment and iterative refinement system.

## Problem Statement

Current validation only checks if the image semantically matches the prompt (CLIP score). This misses:
- **Technical quality**: Jagged edges, blurry areas, compression artifacts
- **Aesthetic quality**: Composition, lighting, visual appeal
- **Detail quality**: Lack of fine details, missing reflections, texture issues
- **Prompt adherence**: Does it actually contain all requested elements?

### Example Issue
> "The space station looks cool from afar, but once I get closer it's jagged and uneven and there are no reflections."

This is a **technical quality** issue that CLIP alone cannot detect.

---

## Quality Scoring Framework

### Multi-Dimensional Quality Score

Each image gets scored on multiple dimensions (0-10 scale):

| Dimension | Metric(s) | What It Measures |
|-----------|-----------|------------------|
| **Technical** | BRISQUE, NIQE | Artifacts, noise, blur, jaggedness |
| **Aesthetic** | LAION Aesthetic, NIMA | Visual appeal, composition, lighting |
| **Prompt Adherence** | CLIP | Does image match text description |
| **Detail** | TOPIQ, Edge sharpness | Fine detail preservation, textures |

### Composite Score Formula

```python
quality_score = (
    0.30 * technical_score +    # Artifacts, sharpness
    0.25 * aesthetic_score +    # Visual appeal
    0.25 * prompt_adherence +   # Matches request
    0.20 * detail_score         # Fine details
)
```

### Quality Grades

| Grade | Score Range | Description |
|-------|-------------|-------------|
| **A** | 8.0 - 10.0 | Production ready, no issues |
| **B** | 6.5 - 7.9 | Good quality, minor issues |
| **C** | 5.0 - 6.4 | Acceptable, noticeable issues |
| **D** | 3.0 - 4.9 | Poor, significant issues |
| **F** | 0.0 - 2.9 | Failed, regenerate |

---

## Metrics Deep Dive

### Technical Quality Metrics

**BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator)**
- No-reference metric for natural image quality
- Detects: blur, noise, compression artifacts
- Range: 0-100 (lower is better) → normalize to 0-10

**NIQE (Natural Image Quality Evaluator)**
- Measures deviation from natural image statistics
- Detects: unnatural textures, synthetic artifacts
- Good for catching AI generation artifacts

### Aesthetic Metrics

**LAION Aesthetic Predictor**
- Trained on human aesthetic preferences
- Predicts how "pleasing" an image is to humans
- Range: 1-10 (higher is better)

**NIMA (Neural Image Assessment)**
- Trained on AVA dataset (aesthetic votes)
- Provides mean and distribution of aesthetic scores

### Detail/Sharpness Metrics

**TOPIQ**
- State-of-the-art perceptual quality
- Good for edge sharpness and detail preservation

**Edge Density**
- Custom metric: ratio of detected edges to image area
- Low edge density = soft/blurry
- Very high edge density = noisy/artifact-y

---

## Iterative Refinement System

### How ChatGPT/DALL-E Does It

1. Generate initial image
2. Use vision model to analyze result
3. Check against prompt requirements
4. If unsatisfactory, adjust parameters and regenerate
5. Repeat until quality threshold met or max attempts

### Our Implementation

```python
def generate_with_refinement(
    prompt: str,
    max_attempts: int = 3,
    quality_threshold: float = 7.0,
    strategy: str = "progressive"
) -> GenerationResult:
    """
    Generate image with iterative quality refinement.
    
    Strategies:
        - "progressive": Increase steps/cfg on retry
        - "seed_search": Try different seeds
        - "prompt_enhance": Add quality boosters on retry
    """
    for attempt in range(max_attempts):
        # Adjust parameters based on strategy and attempt
        params = get_retry_params(attempt, strategy)
        
        # Generate
        image_path = generate_image(prompt, **params)
        
        # Score quality
        scores = quality_scorer.score(image_path, prompt)
        
        if scores.composite >= quality_threshold:
            return GenerationResult(
                image_path=image_path,
                scores=scores,
                attempts=attempt + 1,
                status="success"
            )
        
        # Log why it failed for learning
        log_quality_failure(prompt, scores)
    
    # Return best attempt even if below threshold
    return GenerationResult(
        image_path=best_image_path,
        scores=best_scores,
        attempts=max_attempts,
        status="best_effort"
    )
```

### Retry Strategies

**Progressive Enhancement**
```
Attempt 1: steps=30, cfg=7.0, seed=random
Attempt 2: steps=50, cfg=7.5, seed=random  
Attempt 3: steps=80, cfg=8.0, seed=random
```

**Seed Search**
```
Attempt 1: steps=50, seed=42
Attempt 2: steps=50, seed=1337
Attempt 3: steps=50, seed=9999
```

**Prompt Enhancement**
```
Attempt 1: original prompt
Attempt 2: prompt + ", highly detailed, sharp focus"
Attempt 3: prompt + ", masterpiece, best quality, 8K, ultra detailed"
```

---

## Enhanced Metadata Schema

```json
{
  "timestamp": "2026-01-04T15:30:00Z",
  "generation_id": "uuid-v4",
  
  "input": {
    "prompt": "A sleek Porsche 911...",
    "negative_prompt": "blurry, low quality...",
    "preset": "automotive_photography"
  },
  
  "workflow": {
    "name": "flux-dev.json",
    "model": "flux1-dev-fp8.safetensors",
    "vae": "ae.safetensors"
  },
  
  "parameters": {
    "seed": 1001,
    "steps": 80,
    "cfg": 8.5,
    "sampler": "dpmpp_2m",
    "scheduler": "normal",
    "resolution": [1024, 1024],
    "loras": [
      {"name": "automotive_v1", "strength": 0.8}
    ]
  },
  
  "quality": {
    "composite_score": 7.8,
    "grade": "B",
    "technical": {
      "brisque": 6.2,
      "niqe": 7.1
    },
    "aesthetic": {
      "laion_aesthetic": 8.2,
      "nima_mean": 7.5
    },
    "prompt_adherence": {
      "clip_score": 0.85
    },
    "detail": {
      "topiq": 7.9,
      "edge_density": 0.42
    }
  },
  
  "refinement": {
    "attempt": 2,
    "max_attempts": 3,
    "strategy": "progressive",
    "previous_scores": [5.2, 7.8]
  },
  
  "storage": {
    "minio_url": "http://192.168.1.215:9000/comfy-gen/...",
    "file_size_bytes": 2456789,
    "format": "png"
  }
}
```

---

## Implementation Plan

### Phase 1: Quality Scoring (Issue #70)
- [ ] Install `pyiqa` library
- [ ] Create `comfy_gen/quality.py` module
- [ ] Implement multi-dimensional scoring
- [ ] Integrate with existing validation flow
- [ ] Update metadata schema

### Phase 2: Iterative Refinement (Issue #71)
- [ ] Add retry logic to generate.py
- [ ] Implement retry strategies
- [ ] Add `--quality-threshold` and `--max-attempts` flags
- [ ] Store refinement history in metadata

### Phase 3: Quality Dashboard (Issue #72)
- [ ] Extend gallery server with quality charts
- [ ] Add filtering by quality grade
- [ ] Show quality breakdown per dimension
- [ ] Track quality trends over time

---

## Dependencies

```bash
# Install quality assessment library
pip install pyiqa

# Key metrics available:
# - brisque (technical)
# - niqe (technical)
# - topiq_nr (detail/perceptual)
# - clipiqa (prompt adherence)
# - laion_aes (aesthetic)
```

---

## CLI Integration

```bash
# Basic generation with quality scoring
python3 generate.py --workflow flux-dev.json \
    --prompt "..." \
    --quality-score \
    --output /tmp/image.png

# Iterative refinement
python3 generate.py --workflow flux-dev.json \
    --prompt "..." \
    --quality-threshold 7.5 \
    --max-attempts 3 \
    --retry-strategy progressive \
    --output /tmp/image.png

# Score existing image
python3 -m comfy_gen.quality /tmp/image.png "original prompt"
```

---

## MCP Server Integration

```python
# New tool: generate_quality
{
    "name": "generate_quality",
    "description": "Generate image with quality scoring and optional refinement",
    "parameters": {
        "prompt": "string",
        "quality_threshold": "float (default 7.0)",
        "max_attempts": "int (default 3)",
        "return_scores": "bool (default true)"
    }
}

# New tool: score_image
{
    "name": "score_image", 
    "description": "Score an existing image's quality",
    "parameters": {
        "image_url": "string (MinIO URL)",
        "prompt": "string (optional, for CLIP scoring)"
    }
}
```

---

## Success Criteria

1. **Quality scores correlate with human judgment** - Test with 20 images, score correlation > 0.7
2. **Iterative refinement improves quality** - Average improvement of +1.5 points on retries
3. **No false positives** - Quality score > 7.0 should never have obvious artifacts
4. **Performance** - Quality scoring < 5 seconds per image (on magneto)

---

## References

- [IQA-PyTorch](https://github.com/chaofengc/IQA-PyTorch) - Comprehensive IQA toolbox
- [LAION Aesthetic](https://github.com/christophschuhmann/improved-aesthetic-predictor) - Aesthetic scoring
- [CLIP](https://openai.com/research/clip) - Text-image similarity
