# Enhanced Metadata JSON Schema

## Overview

This document describes the enhanced metadata JSON schema implemented to support comprehensive experiment tracking and reproducibility for image generation.

## Schema Comparison

### Old Flat Format (Before Enhancement)

```json
{
  "timestamp": "2026-01-04T13:40:36",
  "prompt": "...",
  "negative_prompt": "...",
  "workflow": "flux-dev.json",
  "seed": 42,
  "steps": 30,
  "cfg": 7,
  "sampler": "dpmpp_2m",
  "scheduler": "normal",
  "loras": [{"name": "...", "strength": 0.9}],
  "preset": null,
  "validation_score": 1.0,
  "minio_url": "..."
}
```

### New Nested Format (After Enhancement)

```json
{
  "timestamp": "2026-01-04T15:30:00Z",
  "generation_id": "550e8400-e29b-41d4-a716-446655440000",
  
  "input": {
    "prompt": "...",
    "negative_prompt": "...",
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
    "loras": [{"name": "...", "strength": 0.8}]
  },
  
  "quality": {
    "composite_score": 7.8,
    "grade": "B",
    "technical": {"brisque": 6.2, "niqe": 7.1},
    "aesthetic": {"laion": 8.2},
    "prompt_adherence": {"clip": 0.85},
    "detail": {"topiq": 7.9}
  },
  
  "refinement": {
    "attempt": 2,
    "max_attempts": 3,
    "strategy": "progressive",
    "previous_scores": [5.2]
  },
  
  "storage": {
    "minio_url": "http://192.168.1.215:9000/comfy-gen/...",
    "file_size_bytes": 2456789,
    "format": "png",
    "generation_time_seconds": 45.2
  }
}
```

## New Features

### 1. Generation Tracking
- **`generation_id`**: UUID for unique identification across systems
- **`timestamp`**: ISO 8601 timestamp for temporal tracking

### 2. Workflow Information (Auto-extracted)
- **`model`**: Base model filename extracted from CheckpointLoader or UNETLoader nodes
- **`vae`**: VAE model extracted from VAELoader node (if present)
- **`name`**: Workflow filename for reference

### 3. Generation Parameters
- **`resolution`**: [width, height] array extracted from EmptyLatentImage node
- All previous parameters preserved (seed, steps, cfg, sampler, scheduler, loras)

### 4. Storage Metadata
- **`file_size_bytes`**: Actual file size for storage tracking
- **`format`**: File format (png, jpg, etc.)
- **`generation_time_seconds`**: Total time from queue to completion
- **`minio_url`**: Storage location URL

### 5. Quality Placeholders (for future integration)
- **`quality.composite_score`**: Overall 0-10 score (Issue #70)
- **`quality.grade`**: Letter grade A/B/C/D/F
- **`quality.technical`**: BRISQUE, NIQE scores
- **`quality.aesthetic`**: LAION aesthetic score
- **`quality.prompt_adherence.clip`**: CLIP score (existing validation_score moved here)
- **`quality.detail`**: TOPIQ score

### 6. Refinement Placeholders (for future integration)
- **`refinement.attempt`**: Which attempt this was (Issue #71)
- **`refinement.max_attempts`**: How many attempts allowed
- **`refinement.strategy`**: What strategy used
- **`refinement.previous_scores`**: Scores from prior attempts

## Backward Compatibility

The gallery server (`scripts/gallery_server.py`) has been updated to handle both formats:

```javascript
// JavaScript parsing logic
if (rawMeta.input) {
    // New nested format
    meta = {
        prompt: rawMeta.input?.prompt || 'No prompt',
        seed: rawMeta.parameters?.seed,
        loras: rawMeta.parameters?.loras || [],
        validation_score: rawMeta.quality?.prompt_adherence?.clip,
        // ... additional fields
    };
} else {
    // Old flat format
    meta = {
        prompt: rawMeta.prompt || 'No prompt',
        seed: rawMeta.seed,
        loras: rawMeta.loras || [],
        validation_score: rawMeta.validation_score
    };
}
```

## Implementation Details

### Auto-extraction Functions

Three new helper functions automatically extract information from workflows:

1. **`extract_model_from_workflow(workflow)`**
   - Searches for CheckpointLoaderSimple or UNETLoader nodes
   - Returns model filename or None

2. **`extract_vae_from_workflow(workflow)`**
   - Searches for VAELoader nodes
   - Returns VAE filename or None

3. **`extract_resolution_from_workflow(workflow)`**
   - Searches for EmptyLatentImage nodes
   - Returns [width, height] array or None

### Timing Tracking

The `run_generation()` function now tracks total generation time:

```python
generation_start_time = time.time()
# ... queue and wait for completion ...
generation_time_seconds = time.time() - generation_start_time
return success, minio_url, object_name, generation_time_seconds
```

### File Size Calculation

File size is calculated when metadata is created if output path exists:

```python
if output_path and os.path.exists(output_path):
    file_size_bytes = os.path.getsize(output_path)
    file_format = Path(output_path).suffix.lstrip('.')
```

## Benefits

1. **Reproducibility**: All parameters needed to recreate a generation are captured
2. **Experiment Tracking**: Quality scores and refinement info enable A/B testing
3. **Resource Monitoring**: File sizes and generation times aid capacity planning
4. **Backward Compatible**: Existing metadata files continue to work
5. **Extensible**: Quality and refinement sections ready for future features

## Usage Example

```python
metadata = create_metadata_json(
    workflow_path="workflows/flux-dev.json",
    prompt="a sleek sports car on a mountain road",
    negative_prompt="bad quality, blurry",
    workflow_params=workflow_params,
    loras=loras_metadata,
    preset="high-quality",
    validation_score=0.87,
    minio_url="http://192.168.1.215:9000/comfy-gen/image.png",
    workflow=workflow,  # NEW: Pass workflow for auto-extraction
    output_path="/tmp/output.png",  # NEW: For file size
    generation_time_seconds=45.2  # NEW: From run_generation
)
```

## Testing

All tests pass:
- `test_metadata.py` - Core extraction and metadata creation
- `test_metadata_schema_example.py` - Full schema demonstration
- `test_metadata_backward_compat.py` - Backward compatibility verification

Run tests: `python3 tests/test_metadata.py`
