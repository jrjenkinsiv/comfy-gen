# Quality System Design

**Last verified:** 2026-01-05

> Design document for ComfyGen's image quality assessment and iterative refinement system.
> Based on academic research: AGIQA-3K, ImageReward, pyiqa benchmarks.

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

## Research Findings

### Key Academic Papers

1. **AGIQA-3K** (IEEE TCSVT 2023) - First comprehensive AGI quality database
   - 2,982 AI-generated images with human MOS scores
   - **Two dimensions**: Perception (technical quality) AND Alignment (prompt match)
   - Finding: These dimensions are NOT correlated - need both!

2. **ImageReward** (NeurIPS 2023) - Human preference reward model
   - Trained on 137k expert comparisons
   - Outperforms CLIP by 38.6%, Aesthetic by 39.6%
   - Specifically designed for text-to-image generation
   - pip installable: `pip install image-reward`

3. **AGIQA-1K** (arXiv 2023) - Perceptual quality assessment
   - Key aspects: technical issues, AI artifacts, unnaturalness, discrepancy, aesthetics
   - Traditional IQA metrics (BRISQUE, NIQE) don't fully capture AI artifacts

### Key Insight: Two Separate Pipelines

The research consistently shows **two orthogonal quality dimensions**:

| Pipeline | What It Measures | Metrics |
|----------|------------------|---------|
| **Validation** | Does image match prompt? | CLIP, ImageReward |
| **Quality** | Is image technically good? | BRISQUE, NIQE, TOPIQ, Aesthetic |

**These are NOT the same thing.** An image can:
- Match the prompt perfectly but look like garbage (low quality, high validation)
- Look beautiful but not match what was requested (high quality, low validation)

---

## CLIP Encoder: Technical Details

### The 77-Token Limit

CLIP (Contrastive Language-Image Pre-training) has a **hard architectural limit of 77 tokens**:

```python
# From CLIP config (CLIPTextConfig)
max_position_embeddings = 77  # Cannot be changed without retraining
```

This is why long, detailed prompts failed with tensor size mismatch errors like:
```
RuntimeError: The size of tensor a (124) must match the size of tensor b (77)
```

### Why ComfyUI GUI Accepts Long Prompts

ComfyUI's Flux model uses **two text encoders**:
1. **CLIP** - 77-token limit (used for image-text matching)
2. **T5** - No token limit (used for primary text conditioning)

The T5 encoder handles the detailed prompt text, while CLIP is used for embedding alignment.
When generating images, T5 processes your full prompt. But for quality scoring and validation,
we need CLIP specifically for image-text similarity scores.

### Prompt Chunking Solution

Following the industry standard (AUTOMATIC1111, Stable Diffusion WebUI), we implement **prompt chunking**:

```
Long prompt → Split into 75-token chunks → Encode each separately → Average embeddings
```

**Implementation (quality.py and validation.py):**

```python
def _chunk_prompt(self, prompt: str, max_chars: int = 250) -> list[str]:
    """Split long prompts into ~77-token chunks (250 chars conservative estimate)."""
    words = prompt.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_len = len(word) + 1
        if current_length + word_len > max_chars and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_len
        else:
            current_chunk.append(word)
            current_length += word_len
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks if chunks else [prompt]

def compute_clip_score(self, image_path: str, prompt: str) -> float:
    chunks = self._chunk_prompt(prompt)
    
    # Get image features once
    image_features = self.clip_model.get_image_features(**image_inputs)
    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
    
    # Process each chunk, average embeddings
    text_embeddings = []
    for chunk in chunks:
        text_features = self.clip_model.get_text_features(**text_inputs)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        text_embeddings.append(text_features)
    
    avg_text_features = torch.stack(text_embeddings).mean(dim=0)
    avg_text_features = avg_text_features / avg_text_features.norm(dim=-1, keepdim=True)
    
    similarity = (image_features @ avg_text_features.T).squeeze()
    return similarity.item()
```

### Best Practices for Prompts

| Use Case | Max Tokens | Recommendation |
|----------|-----------|----------------|
| Quality scoring | Unlimited | Use detailed 100-200 token prompts |
| Validation | Unlimited | Same prompt as generation |
| Simple images | ~50-70 | Keep concise for faster processing |

**Key insight**: With chunking, longer prompts actually **improve** quality scores because they provide more semantic signal. Use detailed, descriptive prompts for best results.

---

## Architecture: Modular Two-Pipeline System

```
┌─────────────────────────────────────────────────────────────────┐
│                        ComfyGen Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  generate.py                                                    │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────┐     ┌──────────────────┐     ┌─────────────────┐  │
│  │ Image   │────▶│ Validation       │────▶│ Quality         │  │
│  │ Output  │     │ Pipeline         │     │ Pipeline        │  │
│  └─────────┘     │                  │     │                 │  │
│                  │ • CLIP Score     │     │ • Technical     │  │
│                  │ • ImageReward    │     │ • Aesthetic     │  │
│                  │ • Prompt Match   │     │ • Detail        │  │
│                  └────────┬─────────┘     └────────┬────────┘  │
│                           │                        │           │
│                           ▼                        ▼           │
│                  ┌─────────────────────────────────────────┐   │
│                  │           Combined Score                │   │
│                  │  validation_score + quality_score       │   │
│                  └─────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline 1: Validation (Existing + Enhanced)

**Purpose**: Does the image match the prompt?

```python
# comfy_gen/validation.py (existing, enhanced)

class ValidationPipeline:
    """Check if image matches what was requested."""
    
    def __init__(self):
        self.clip_model = load_clip()
        self.image_reward = load_image_reward()  # NEW
    
    def score(self, image_path: str, prompt: str, negative_prompt: str = None) -> ValidationResult:
        return ValidationResult(
            clip_score=self.compute_clip_score(image_path, prompt),
            image_reward_score=self.compute_image_reward(image_path, prompt),  # NEW
            prompt_elements_found=self.check_prompt_elements(image_path, prompt),  # NEW
            passed=...,
            grade=...
        )
```

**Metrics**:
| Metric | Library | What It Measures |
|--------|---------|------------------|
| CLIP Score | transformers | Semantic similarity text↔image |
| ImageReward | image-reward | Human preference for T2I |
| Element Detection | (custom) | Are requested objects present? |

### Pipeline 2: Quality (NEW)

**Purpose**: Is the image technically good, regardless of prompt?

```python
# comfy_gen/quality.py (NEW)

class QualityPipeline:
    """Assess technical and aesthetic quality of image."""
    
    def __init__(self):
        self.technical_metrics = load_pyiqa(['brisque', 'niqe'])
        self.aesthetic_model = load_laion_aesthetic()
        self.detail_metrics = load_pyiqa(['topiq_nr'])
    
    def score(self, image_path: str) -> QualityResult:
        return QualityResult(
            technical=TechnicalScore(
                brisque=...,  # Artifacts, noise (lower=better, normalize)
                niqe=...,     # Naturalness (lower=better, normalize)
            ),
            aesthetic=AestheticScore(
                laion_aesthetic=...,  # 1-10 scale, higher=better
            ),
            detail=DetailScore(
                topiq=...,    # Perceptual quality
                sharpness=...,  # Edge detection based
            ),
            composite=...,
            grade=...
        )
```

**Metrics**:
| Metric | Library | What It Measures | Scale |
|--------|---------|------------------|-------|
| BRISQUE | pyiqa | Artifacts, noise, blur | 0-100 (lower=better) |
| NIQE | pyiqa | Deviation from natural | 0-100 (lower=better) |
| TOPIQ | pyiqa | Perceptual quality | 0-1 (higher=better) |
| LAION Aesthetic | aesthetic-predictor | Visual appeal | 1-10 (higher=better) |
| Sharpness | custom | Edge density ratio | 0-1 (higher=better) |

---

## Scoring System

### Combined Score Formula

**Validation Score** (0-10): Does it match the prompt?
```python
validation_score = (
    0.40 * normalize(clip_score) +      # Semantic match
    0.60 * normalize(image_reward)      # Human preference
)
```

**Quality Score** (0-10): Is it technically good?
```python
quality_score = (
    0.35 * normalize_inverse(brisque) +  # Technical (inverted)
    0.25 * laion_aesthetic +              # Aesthetic (already 1-10)
    0.25 * normalize(topiq) * 10 +        # Detail
    0.15 * normalize_inverse(niqe)        # Naturalness (inverted)
)
```

**Final Combined Score**:
```python
combined_score = (
    0.50 * validation_score +  # Equal weight
    0.50 * quality_score
)
```

### Grade Thresholds

| Grade | Combined Score | Meaning |
|-------|----------------|---------|
| **A** | 8.0+ | Excellent - Production ready |
| **B** | 6.5 - 7.9 | Good - Minor issues |
| **C** | 5.0 - 6.4 | Acceptable - Noticeable issues |
| **D** | 3.0 - 4.9 | Poor - Significant issues |
| **F** | < 3.0 | Failed - Regenerate |

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

---

**Documentation Policy:** This is an authoritative reference document. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only. See [copilot-instructions.md](../.github/copilot-instructions.md) for details.
