# API Reference

**Last verified:** 2026-01-05

This document provides technical documentation for ComfyGen's internal modules and functions.

## Table of Contents

- [generate.py](#generatepy)
- [comfy_gen.validation](#comfy_genvalidation)
- [Scripts](#scripts)
- [Code Examples](#code-examples)

---

## generate.py

Main generation script with CLI interface.

### Functions

#### `check_server_availability() -> bool`

Check if ComfyUI server is reachable.

**Returns:** `True` if server is available at `COMFYUI_HOST`, `False` otherwise

**Example:**
```python
if not check_server_availability():
    print("Server is down")
    sys.exit(2)
```

---

#### `get_available_models() -> dict | None`

Query available models from ComfyUI API.

**Returns:** Dictionary with model types as keys:
- `checkpoints`: List of available checkpoint models
- `loras`: List of available LoRA files
- `vae`: List of available VAE models

Returns `None` on failure.

**Example:**
```python
models = get_available_models()
if models:
    print(f"Available checkpoints: {models['checkpoints']}")
```

---

#### `find_model_fallbacks(requested_model: str, available_models: dict, model_type: str = "checkpoints") -> list`

Suggest fallback models when requested model is not found.

**Parameters:**
- `requested_model`: The model that was requested
- `available_models`: Dictionary from `get_available_models()`
- `model_type`: Model category (`"checkpoints"`, `"loras"`, `"vae"`)

**Returns:** List of up to 5 suggested alternative models

**Example:**
```python
models = get_available_models()
fallbacks = find_model_fallbacks("custom-model.safetensors", models, "checkpoints")
print(f"Suggested alternatives: {fallbacks}")
```

---

#### `validate_workflow_models(workflow: dict, available_models: dict) -> tuple`

Validate that all models referenced in workflow exist on the server.

**Parameters:**
- `workflow`: Workflow dictionary loaded from JSON
- `available_models`: Dictionary from `get_available_models()`

**Returns:** Tuple of `(is_valid, missing_models, suggestions)`:
- `is_valid` (bool): `True` if all models exist
- `missing_models` (list): List of `(model_type, model_name)` tuples for missing models
- `suggestions` (dict): Maps missing model names to lists of suggested alternatives

**Example:**
```python
workflow = load_workflow("workflows/flux-dev.json")
models = get_available_models()
is_valid, missing, suggestions = validate_workflow_models(workflow, models)

if not is_valid:
    for model_type, model_name in missing:
        print(f"Missing {model_type}: {model_name}")
        if model_name in suggestions:
            print(f"  Try: {suggestions[model_name]}")
```

---

#### `load_workflow(workflow_path: str) -> dict`

Load workflow JSON from file.

**Parameters:**
- `workflow_path`: Path to workflow JSON file

**Returns:** Workflow dictionary

**Raises:** 
- `FileNotFoundError`: Workflow file doesn't exist
- `json.JSONDecodeError`: Invalid JSON syntax

---

#### `modify_prompt(workflow: dict, positive_prompt: str, negative_prompt: str = "") -> dict`

Modify positive and negative prompts in workflow.

**Parameters:**
- `workflow`: Workflow dictionary
- `positive_prompt`: Text for positive prompt
- `negative_prompt`: Text for negative prompt (optional)

**Returns:** Modified workflow dictionary

**Note:** Modifies nodes 2 (positive) and 3 (negative) in-place and returns the workflow.

---

#### `modify_input_image(workflow: dict, uploaded_filename: str) -> dict`

Update LoadImage nodes in workflow to use specified image.

**Parameters:**
- `workflow`: Workflow dictionary
- `uploaded_filename`: Filename of uploaded image (from `upload_image_to_comfyui()`)

**Returns:** Modified workflow dictionary

---

#### `modify_denoise(workflow: dict, denoise_value: float) -> dict`

Set denoise strength in KSampler nodes.

**Parameters:**
- `workflow`: Workflow dictionary
- `denoise_value`: Denoise strength (0.0-1.0)

**Returns:** Modified workflow dictionary

---

#### `queue_workflow(workflow: dict, retry: bool = True) -> str | None`

Send workflow to ComfyUI server with automatic retry logic.

**Parameters:**
- `workflow`: Workflow dictionary to queue
- `retry`: Enable automatic retry on transient failures (default: `True`)

**Returns:** `prompt_id` string on success, `None` on failure

**Retry Behavior:**
- Maximum retries: 3 (`MAX_RETRIES`)
- Initial delay: 2 seconds (`RETRY_DELAY`)
- Backoff multiplier: 2x (`RETRY_BACKOFF`)
- Only retries on 5xx errors, connection errors, and timeouts
- Does NOT retry on 4xx client errors

**Example:**
```python
prompt_id = queue_workflow(workflow)
if prompt_id:
    print(f"Queued as {prompt_id}")
    status = wait_for_completion(prompt_id)
```

---

#### `wait_for_completion(prompt_id: str) -> dict`

Poll ComfyUI server until workflow completes.

**Parameters:**
- `prompt_id`: Prompt ID returned by `queue_workflow()`

**Returns:** History status dictionary with workflow outputs

**Note:** Polls every 5 seconds. Blocks until completion.

---

#### `download_output(status: dict, output_path: str) -> bool`

Download generated image from ComfyUI to local file.

**Parameters:**
- `status`: Status dictionary from `wait_for_completion()`
- `output_path`: Local path to save the image

**Returns:** `True` on success, `False` on failure

---

#### `upload_to_minio(file_path: str, object_name: str) -> str | None`

Upload file to MinIO bucket with public access.

**Parameters:**
- `file_path`: Local file path
- `object_name`: Object name in MinIO bucket

**Returns:** Public URL to the uploaded file, or `None` on failure

**Example:**
```python
url = upload_to_minio("/tmp/output.png", "20260104_120000_output.png")
if url:
    print(f"Available at: {url}")
```

---

#### `upload_image_to_comfyui(image_path: str) -> str | None`

Upload image to ComfyUI input directory.

**Parameters:**
- `image_path`: Local path to image file

**Returns:** Uploaded filename (without path) or `None` on failure

**Note:** Generates unique filename to avoid conflicts.

---

#### `preprocess_image(image_path: str, resize: tuple | None = None, crop: str | None = None) -> str`

Resize and crop image according to specified options.

**Parameters:**
- `image_path`: Path to input image (modified in-place)
- `resize`: Tuple of `(width, height)` or `None`
- `crop`: Crop mode (`'center'`, `'cover'`, `'contain'`) or `None`

**Returns:** Path to processed image (same as input)

**Crop Modes:**
- `'cover'`: Scale to cover target, crop excess (no black bars)
- `'contain'`: Scale to fit inside target, pad with black bars
- `'center'`: Simple resize and center crop

---

#### `adjust_prompt_for_retry(positive_prompt: str, negative_prompt: str, attempt: int) -> tuple`

Adjust prompts for retry attempt to improve generation quality.

**Parameters:**
- `positive_prompt`: Original positive prompt
- `negative_prompt`: Original negative prompt
- `attempt`: Current retry attempt number (1-based)

**Returns:** Tuple of `(adjusted_positive, adjusted_negative)`

**Adjustments:**
- Increases weight on key terms like "single" → `(single:1.3)`
- Adds negative terms: "duplicate, cloned, ghosting, mirrored"
- Weight multiplier increases with each attempt

---

#### `get_retry_params(attempt: int, strategy: str, base_steps: int = None, base_cfg: float = None, base_seed: int = None, base_prompt: str = "", base_negative: str = "") -> dict`

Get adjusted parameters for retry attempt based on refinement strategy.

**Parameters:**
- `attempt`: Current attempt number (1-based, where 1 is initial attempt)
- `strategy`: Retry strategy - `'progressive'`, `'seed_search'`, or `'prompt_enhance'`
- `base_steps`: Base number of steps (default: 30 if None)
- `base_cfg`: Base CFG scale (default: 7.0 if None)
- `base_seed`: Base random seed (default: random if None)
- `base_prompt`: Original positive prompt
- `base_negative`: Original negative prompt

**Returns:** Dictionary with keys:
- `steps` (int): Adjusted step count
- `cfg` (float): Adjusted CFG scale (capped at 20.0)
- `seed` (int): Seed for this attempt
- `positive_prompt` (str): Adjusted positive prompt
- `negative_prompt` (str): Adjusted negative prompt

**Strategy Behaviors:**

*Progressive Enhancement:*
```python
# Attempt 1: steps=30, cfg=7.0, seed=random
# Attempt 2: steps=50, cfg=7.5, seed=random
# Attempt 3: steps=80, cfg=8.0, seed=random
```

*Seed Search:*
```python
# Attempt 1: seed=base+0
# Attempt 2: seed=base+1000
# Attempt 3: seed=base+5000
# (Steps/CFG unchanged, prompts unchanged)
```

*Prompt Enhancement:*
```python
# Attempt 1: original prompt
# Attempt 2: prompt + ", highly detailed, sharp focus"
# Attempt 3: prompt + ", masterpiece, best quality, 8K, ultra detailed"
# (New seed each attempt)
```

**Example:**
```python
# Get parameters for second attempt using progressive strategy
params = get_retry_params(
    attempt=2,
    strategy='progressive',
    base_steps=30,
    base_cfg=7.0,
    base_seed=42,
    base_prompt="a sunset",
    base_negative="blurry"
)
# Returns: {'steps': 50, 'cfg': 7.5, 'seed': <random>, 'positive_prompt': "a sunset", 'negative_prompt': "blurry"}

# Apply to workflow
workflow = modify_sampler_params(workflow, steps=params['steps'], cfg=params['cfg'], seed=params['seed'])
workflow = modify_prompt(workflow, params['positive_prompt'], params['negative_prompt'])
```

---

#### `cancel_prompt(prompt_id: str) -> bool`

Cancel a specific queued or running prompt.

**Parameters:**
- `prompt_id`: Prompt ID to cancel

**Returns:** `True` on success, `False` on failure

**Actions:**
1. Sends interrupt signal
2. Deletes from queue

---

## comfy_gen.validation

Image validation module using CLIP for semantic similarity.

### Classes

#### `ImageValidator`

CLIP-based image validator.

**Constructor:**
```python
ImageValidator(model_name: str = "openai/clip-vit-base-patch32")
```

**Parameters:**
- `model_name`: HuggingFace CLIP model identifier

**Attributes:**
- `device`: `"cuda"` or `"cpu"`
- `model`: Loaded CLIP model
- `processor`: CLIP processor for inputs

---

### Methods

#### `compute_clip_score(image_path: str, positive_prompt: str, negative_prompt: str | None = None) -> dict`

Compute CLIP similarity scores for an image.

**Parameters:**
- `image_path`: Path to generated image
- `positive_prompt`: Positive text prompt
- `negative_prompt`: Optional negative prompt

**Returns:** Dictionary with:
- `positive_score` (float): Similarity to positive prompt (0-1)
- `negative_score` (float): Similarity to negative prompt (if provided)
- `score_delta` (float): `positive_score - negative_score` (if both available)
- `error` (str): Error message if computation failed

**Example:**
```python
validator = ImageValidator()
scores = validator.compute_clip_score(
    "/tmp/car.png",
    "a red sports car",
    "multiple cars, duplicate"
)
print(f"Positive score: {scores['positive_score']:.3f}")
print(f"Delta: {scores.get('score_delta', 0.0):.3f}")
```

---

#### `validate_image(image_path: str, positive_prompt: str, negative_prompt: str | None = None, positive_threshold: float = 0.25, delta_threshold: float | None = None) -> dict`

Validate image against prompt constraints.

**Parameters:**
- `image_path`: Path to generated image
- `positive_prompt`: Positive text prompt
- `negative_prompt`: Optional negative prompt
- `positive_threshold`: Minimum acceptable positive CLIP score (default: 0.25)
- `delta_threshold`: Minimum acceptable delta (if negative prompt provided)

**Returns:** Dictionary with:
- `passed` (bool): Validation result
- `reason` (str): Failure reason or success message
- `positive_score` (float): Positive CLIP score
- `negative_score` (float): Negative CLIP score (if applicable)
- `score_delta` (float): Score delta (if applicable)

**Example:**
```python
validator = ImageValidator()
result = validator.validate_image(
    "/tmp/car.png",
    "a red sports car",
    "multiple cars",
    positive_threshold=0.28
)

if result['passed']:
    print(f"Validation passed! Score: {result['positive_score']:.3f}")
else:
    print(f"Validation failed: {result['reason']}")
```

---

### Module-Level Functions

#### `validate_image(...) -> dict`

Convenience function that creates a new `ImageValidator` instance for single-use validation.

**Signature:** Same as `ImageValidator.validate_image()`

**Example:**
```python
from comfy_gen.validation import validate_image

result = validate_image(
    "/tmp/output.png",
    "a beautiful sunset",
    positive_threshold=0.25
)
print(f"Passed: {result['passed']}")
```

---

## Scripts

Utility scripts in `scripts/` directory.

### Service Management

#### `start_comfyui.py`

Start ComfyUI server on moira as a background process.

**Usage:**
```bash
python3 scripts/start_comfyui.py
```

**Returns:** Exit code 0 on success, 1 on failure

---

#### `stop_comfyui.py`

Stop running ComfyUI server.

**Usage:**
```bash
python3 scripts/stop_comfyui.py
```

**Returns:** Exit code 0 on success, 1 on failure or if not running

---

#### `restart_comfyui.py`

Restart ComfyUI server (stop then start).

**Usage:**
```bash
python3 scripts/restart_comfyui.py
```

---

#### `check_comfyui_status.py`

Check ComfyUI server status (process and API health).

**Usage:**
```bash
python3 scripts/check_comfyui_status.py
```

**Output:** Status report with process state and API availability

---

### Generation Management

#### `cancel_generation.py`

Cancel running or queued generation jobs.

**Usage:**
```bash
# Cancel all jobs
python3 scripts/cancel_generation.py

# List queue
python3 scripts/cancel_generation.py --list

# Cancel specific prompt
python3 scripts/cancel_generation.py --prompt-id <id>
```

---

### MinIO Management

#### `set_bucket_policy.py`

Make MinIO bucket publicly readable.

**Usage:**
```bash
python3 scripts/set_bucket_policy.py
```

---

#### `create_bucket.py`

Create the comfy-gen MinIO bucket.

**Usage:**
```bash
python3 scripts/create_bucket.py
```

---

#### `list_images.py`

List all images in MinIO bucket.

**Usage:**
```bash
python3 scripts/list_images.py
```

---

## Code Examples

### End-to-End Generation

```python
#!/usr/bin/env python3
"""Complete generation example with error handling."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate import (
    check_server_availability,
    load_workflow,
    get_available_models,
    validate_workflow_models,
    modify_prompt,
    queue_workflow,
    wait_for_completion,
    download_output,
    upload_to_minio,
    EXIT_SUCCESS,
    EXIT_CONFIG_ERROR
)

def main():
    # Check server
    if not check_server_availability():
        print("[ERROR] Server unavailable")
        return EXIT_CONFIG_ERROR
    
    # Load and validate workflow
    workflow = load_workflow("workflows/flux-dev.json")
    models = get_available_models()
    
    if models:
        is_valid, missing, suggestions = validate_workflow_models(workflow, models)
        if not is_valid:
            print(f"[ERROR] Missing models: {missing}")
            return EXIT_CONFIG_ERROR
    
    # Modify prompts
    workflow = modify_prompt(
        workflow,
        "a beautiful mountain landscape at sunset",
        "blurry, low quality"
    )
    
    # Queue and wait
    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        print("[ERROR] Failed to queue")
        return 1
    
    status = wait_for_completion(prompt_id)
    
    # Download and upload
    output_path = "/tmp/landscape.png"
    if download_output(status, output_path):
        url = upload_to_minio(output_path, "landscape.png")
        if url:
            print(f"[OK] Available at: {url}")
            return EXIT_SUCCESS
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Validation Workflow

```python
#!/usr/bin/env python3
"""Example using validation with retry loop."""

from comfy_gen.validation import ImageValidator
from generate import (
    load_workflow,
    modify_prompt,
    queue_workflow,
    wait_for_completion,
    download_output,
    adjust_prompt_for_retry
)

def generate_with_validation(prompt, negative_prompt="", max_retries=3):
    """Generate image with automatic validation and retry."""
    validator = ImageValidator()
    workflow = load_workflow("workflows/flux-dev.json")
    
    for attempt in range(1, max_retries + 1):
        print(f"[INFO] Attempt {attempt}/{max_retries}")
        
        # Adjust prompts for retry
        if attempt > 1:
            prompt, negative_prompt = adjust_prompt_for_retry(
                prompt, negative_prompt, attempt - 1
            )
            print(f"[INFO] Adjusted prompt: {prompt}")
        
        # Generate
        workflow = modify_prompt(workflow, prompt, negative_prompt)
        prompt_id = queue_workflow(workflow)
        if not prompt_id:
            continue
        
        status = wait_for_completion(prompt_id)
        output_path = f"/tmp/attempt_{attempt}.png"
        
        if not download_output(status, output_path):
            continue
        
        # Validate
        result = validator.validate_image(
            output_path,
            prompt,
            negative_prompt,
            positive_threshold=0.25
        )
        
        print(f"[INFO] Score: {result['positive_score']:.3f}")
        
        if result['passed']:
            print("[OK] Validation passed!")
            return output_path
        else:
            print(f"[WARN] Failed: {result['reason']}")
    
    return None

# Usage
output = generate_with_validation(
    "(Porsche 911:2.0) single car, driving",
    "multiple cars, duplicate"
)
```

### Batch Processing

```python
#!/usr/bin/env python3
"""Generate multiple images in batch."""

from generate import *
import time

prompts = [
    "a sunset over mountains",
    "a sports car on a highway",
    "a serene lake with reflections",
]

workflow = load_workflow("workflows/flux-dev.json")

for i, prompt in enumerate(prompts):
    print(f"\n[INFO] Generating {i+1}/{len(prompts)}: {prompt}")
    
    workflow = modify_prompt(workflow, prompt, "blurry, low quality")
    prompt_id = queue_workflow(workflow)
    
    if prompt_id:
        status = wait_for_completion(prompt_id)
        output_path = f"/tmp/batch_{i}.png"
        
        if download_output(status, output_path):
            url = upload_to_minio(output_path, f"batch_{i}.png")
            print(f"[OK] {url}")
    
    time.sleep(2)  # Rate limiting
```

---

## MCP Server API

The MCP server provides tools for AI-driven image generation with progress tracking.

### New Features (Progress Tracking & Local Output)

#### `generate_image` Tool

Enhanced with progress tracking and local file output capabilities.

**New Parameters:**
- `output_path` (str, optional): Local file path to save the generated image (in addition to MinIO storage)
- `json_progress` (bool, default=False): Enable structured JSON progress updates during generation

**Returns:**
Enhanced response with:
- `local_path` (str): Path to locally saved file if `output_path` was provided
- `progress_updates` (list): Array of progress update objects if `json_progress=True`

**Progress Update Format:**
```json
{
  "type": "progress",
  "prompt_id": "abc123",
  "step": 15,
  "max_steps": 30,
  "percent": 50,
  "eta_seconds": 12.5,
  "message": "Sampling: 15/30 steps (50%)"
}
```

**Progress Update Types:**
- `connected`: WebSocket connection established
- `start`: Generation started
- `progress`: Sampling progress update
- `node`: Node execution update
- `cached`: Cached results being used
- `complete`: Generation completed
- `error`: Error occurred

**Example:**
```python
result = await generate_image(
    prompt="a sunset over mountains",
    output_path="/tmp/sunset.png",
    json_progress=True
)

# Result includes:
# - url: MinIO URL for web access
# - local_path: Local file path
# - progress_updates: List of all progress events
```

---

#### `validate_workflow` Tool

Validate workflow without executing it (dry run).

**Parameters:**
- `model` (str): Model to use (sd15, flux, sdxl)
- `prompt` (str): Test prompt for validation
- `width` (int): Output width
- `height` (int): Output height

**Returns:**
```json
{
  "status": "valid" | "invalid",
  "workflow_file": "flux-dev.json",
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "missing_models": []
}
```

**Example:**
```python
# Validate before generating
validation = await validate_workflow(
    model="sd15",
    prompt="test",
    width=512,
    height=512
)

if validation["is_valid"]:
    # Proceed with generation
    result = await generate_image(...)
else:
    print(f"Errors: {validation['errors']}")
```

---

#### `get_progress` Tool

Get real-time progress for a specific generation job.

**Parameters:**
- `prompt_id` (str, optional): Specific prompt ID to check. If not provided, returns general queue status.

**Returns:**
```json
{
  "status": "running" | "pending" | "completed" | "not_found",
  "prompt_id": "abc123",
  "position": "current" | 1,
  "queue_length": 3
}
```

**Example:**
```python
# Start generation
result = await generate_image(prompt="...", json_progress=False)
prompt_id = result["prompt_id"]

# Poll for progress
while True:
    progress = await get_progress(prompt_id)
    if progress["status"] == "completed":
        break
    time.sleep(2)
```

---

## See Also

- [USAGE.md](USAGE.md) - Complete usage guide for CLI and MCP
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and workflows
- [MODEL_REGISTRY.md](MODEL_REGISTRY.md) - Available models

---

**Documentation Policy:** This is an authoritative reference document. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only.
