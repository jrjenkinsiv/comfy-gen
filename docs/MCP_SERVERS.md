# MCP Server Tools Reference

This document provides detailed documentation for all MCP (Model Context Protocol) tools exposed by the ComfyGen server.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Model Discovery Tools](#model-discovery-tools)
  - [CivitAI Tools](#civitai-tools)
  - [HuggingFace Hub Tools](#huggingface-hub-tools)
- [Core Generation Tools](#core-generation-tools)
- [Model Management Tools](#model-management-tools)
- [Gallery & History Tools](#gallery--history-tools)
- [Prompt Engineering Tools](#prompt-engineering-tools)
- [Progress & Control Tools](#progress--control-tools)
- [Service Management Tools](#service-management-tools)

---

## Overview

The ComfyGen MCP server provides **29+ tools** for AI-driven image/video generation. These tools enable AI assistants like Claude Desktop to:

- Discover and download models from CivitAI and HuggingFace Hub
- Generate images and videos with ComfyUI
- Manage models, LoRAs, and generation parameters
- Track progress and manage the generation queue
- Analyze and enhance prompts
- Browse and manage generated images

---

## Setup

Add to your MCP client configuration (VS Code, Claude Desktop, etc.):

```json
{
  "mcpServers": {
    "comfy-gen": {
      "command": "python3",
      "args": ["/path/to/comfy-gen/mcp_server.py"],
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000",
        "MINIO_BUCKET": "comfy-gen",
        "CIVITAI_API_KEY": "${CIVITAI_API_KEY}",
        "HF_TOKEN": "${HF_TOKEN}"
      }
    }
  }
}
```

**Environment Variables:**
- `COMFYUI_HOST` - ComfyUI server URL (default: http://192.168.1.215:8188)
- `MINIO_ENDPOINT` - MinIO storage endpoint (default: 192.168.1.215:9000)
- `MINIO_BUCKET` - MinIO bucket name (default: comfy-gen)
- `CIVITAI_API_KEY` - Optional CivitAI API key for NSFW content and downloads
- `HF_TOKEN` - Optional HuggingFace token for gated models and private repos

---

## Model Discovery Tools

### CivitAI Tools

#### `search_civitai(query, model_type, base_model, sort, nsfw, limit)`

Search CivitAI for models and LoRAs.

**Parameters:**
- `query` (str): Search query
- `model_type` (str): Filter by type - "all", "checkpoint", "lora", "vae" (default: "all")
- `base_model` (str, optional): Filter by base model - "SD 1.5", "SDXL", etc.
- `sort` (str): Sort method - "Most Downloaded", "Highest Rated", "Newest" (default: "Most Downloaded")
- `nsfw` (bool): Include NSFW results (default: True)
- `limit` (int): Maximum results (default: 10)

**Returns:**
```json
{
  "status": "success",
  "results": [
    {
      "id": 12345,
      "name": "Example Model",
      "type": "LORA",
      "description": "A LoRA for...",
      "creator": "username",
      "downloads": 50000,
      "rating": 4.8,
      "base_model": "SD 1.5",
      "version_id": 67890,
      "preview_url": "https://...",
      "download_url": "https://...",
      "nsfw": false
    }
  ],
  "count": 1
}
```

**Example:**
```python
# Search for SD 1.5 LoRAs
result = await search_civitai(
    query="detailed skin texture",
    model_type="lora",
    base_model="SD 1.5",
    limit=5
)
```

---

### HuggingFace Hub Tools

#### `hf_search_models(query, library, pipeline_tag, tags, sort, limit)`

Search HuggingFace Hub for models.

**Parameters:**
- `query` (str): Search query (searches in model name and description, default: "")
- `library` (str, optional): Filter by library - "diffusers", "transformers", etc.
- `pipeline_tag` (str, optional): Filter by pipeline tag - "text-to-image", "image-to-image", etc.
- `tags` (list, optional): Additional tags to filter by, e.g., ["sdxl", "flux", "lora"]
- `sort` (str): Sort method - "downloads", "likes", "trending", "updated" (default: "downloads")
- `limit` (int): Maximum results (default: 10)

**Returns:**
```json
{
  "status": "success",
  "results": [
    {
      "id": "black-forest-labs/FLUX.1-dev",
      "name": "FLUX.1-dev",
      "author": "black-forest-labs",
      "downloads": 1000000,
      "likes": 5000,
      "tags": ["diffusers", "text-to-image", "flux"],
      "pipeline_tag": "text-to-image",
      "library_name": "diffusers",
      "created_at": "2024-08-01T10:00:00",
      "last_modified": "2024-08-15T14:30:00",
      "private": false,
      "gated": false
    }
  ],
  "count": 1
}
```

**Example:**
```python
# Search for Flux diffusion models
result = await hf_search_models(
    query="flux",
    library="diffusers",
    pipeline_tag="text-to-image",
    limit=5
)
```

#### `hf_get_model_info(model_id)`

Get detailed information about a HuggingFace model.

**Parameters:**
- `model_id` (str): HuggingFace model ID (e.g., "black-forest-labs/FLUX.1-dev")

**Returns:**
```json
{
  "status": "success",
  "model": {
    "id": "black-forest-labs/FLUX.1-dev",
    "author": "black-forest-labs",
    "sha": "abc123...",
    "created_at": "2024-08-01T10:00:00",
    "last_modified": "2024-08-15T14:30:00",
    "private": false,
    "gated": false,
    "downloads": 1000000,
    "likes": 5000,
    "tags": ["diffusers", "text-to-image", "flux"],
    "pipeline_tag": "text-to-image",
    "library_name": "diffusers",
    "model_card": "# FLUX.1-dev\n\nFLUX.1 [dev] is a 12 billion...",
    "siblings_count": 15
  }
}
```

**Example:**
```python
# Get info about FLUX model
result = await hf_get_model_info("black-forest-labs/FLUX.1-dev")
```

#### `hf_list_files(model_id)`

List files in a HuggingFace model repository.

**Parameters:**
- `model_id` (str): HuggingFace model ID

**Returns:**
```json
{
  "status": "success",
  "files": [
    {
      "filename": "diffusion_pytorch_model.safetensors",
      "size": 23622320128,
      "blob_id": "abc123...",
      "lfs": {
        "oid": "sha256:...",
        "size": 23622320128
      }
    },
    {
      "filename": "model_index.json",
      "size": 543,
      "blob_id": "def456...",
      "lfs": null
    }
  ],
  "count": 2
}
```

**Example:**
```python
# List files in a model repo
result = await hf_list_files("black-forest-labs/FLUX.1-dev")
```

#### `hf_download(model_id, filename, local_dir)`

Download a file from HuggingFace Hub.

**Parameters:**
- `model_id` (str): HuggingFace model ID
- `filename` (str): Filename to download (e.g., "diffusion_pytorch_model.safetensors")
- `local_dir` (str, optional): Local directory to save file (uses HF cache if not provided)

**Returns:**
```json
{
  "status": "success",
  "filepath": "/home/user/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-dev/snapshots/abc123.../diffusion_pytorch_model.safetensors",
  "model_id": "black-forest-labs/FLUX.1-dev",
  "filename": "diffusion_pytorch_model.safetensors"
}
```

**Example:**
```python
# Download model to specific directory
result = await hf_download(
    model_id="black-forest-labs/FLUX.1-dev",
    filename="diffusion_pytorch_model.safetensors",
    local_dir="/models/checkpoints"
)
```

**Notes:**
- Requires `HF_TOKEN` environment variable for gated models
- Some models require accepting terms on HuggingFace website first
- Files are cached by default in `~/.cache/huggingface/hub/`

---

## Core Generation Tools

### `generate_image(prompt, negative_prompt, model, width, height, steps, cfg, sampler, scheduler, seed, loras, preset, lora_preset, output_path, json_progress, validate, auto_retry, retry_limit, positive_threshold)`

Generate an image from a text prompt.

**Parameters:**
- `prompt` (str): What to generate
- `negative_prompt` (str, optional): What to avoid (default: "blurry, low quality, watermark")
- `model` (str): Model to use - "sd15", "flux", "sdxl" (default: "sd15")
- `width` (int): Image width (default: 512)
- `height` (int): Image height (default: 512)
- `steps` (int): Sampling steps (default: 20)
- `cfg` (float): CFG scale (default: 7.0)
- `sampler` (str): Sampler algorithm (default: "euler")
- `scheduler` (str): Scheduler type (default: "normal")
- `seed` (int): Random seed, -1 for random (default: -1)
- `loras` (list, optional): LoRAs to apply, e.g., [{"name": "lora.safetensors", "strength": 0.8}]
- `preset` (str, optional): Generation preset - "draft", "balanced", "high-quality", "fast", "ultra"
- `lora_preset` (str, optional): LoRA preset from lora_catalog.yaml
- `output_path` (str, optional): Local file path to save image
- `json_progress` (bool): Enable structured progress updates (default: False)
- `validate` (bool, optional): Run CLIP validation
- `auto_retry` (bool, optional): Auto-retry if validation fails
- `retry_limit` (int, optional): Max retry attempts (default: 3)
- `positive_threshold` (float, optional): Min CLIP score (default: 0.25)

**Returns:**
```json
{
  "status": "success",
  "url": "http://192.168.1.215:9000/comfy-gen/20240815_143045_sunset.png",
  "local_path": "/tmp/sunset.png",
  "prompt_id": "abc123...",
  "metadata": {
    "prompt": "a sunset over mountains",
    "model": "sd15",
    "steps": 20,
    "cfg": 7.0,
    "seed": 12345
  },
  "progress_updates": [...]
}
```

**Example:**
```python
# Generate with preset and local output
result = await generate_image(
    prompt="a sunset over mountains, cinematic lighting",
    preset="high-quality",
    output_path="/tmp/sunset.png",
    json_progress=True
)
```

### `img2img(input_image, prompt, negative_prompt, denoise, ...)`

Transform an existing image with prompt guidance.

**Additional Parameters:**
- `input_image` (str): URL or path to input image
- `denoise` (float): Strength 0.0-1.0 (default: 0.7)

---

## Model Management Tools

### `list_models()`

List installed checkpoint models.

**Returns:**
```json
{
  "status": "success",
  "checkpoints": ["sd_xl_base_1.0.safetensors", "v1-5-pruned-emaonly.safetensors"],
  "diffusion_models": ["wan_2.2_diffusion_model.safetensors"],
  "vae": ["vae-ft-mse-840000-ema-pruned.safetensors"],
  "count": 2
}
```

### `list_loras()`

List installed LoRAs with compatibility info.

**Returns:**
```json
{
  "status": "success",
  "loras": [
    {
      "name": "polyhedron_skin.safetensors",
      "tags": ["skin", "realism", "texture"],
      "compatible_with": ["SD 1.5"],
      "recommended_strength": 0.8,
      "description": "Detailed skin texture enhancement"
    }
  ],
  "count": 1
}
```

### `get_model_info(model_name)`

Get detailed metadata about a model.

**Parameters:**
- `model_name` (str): Model filename

**Returns:**
```json
{
  "status": "success",
  "name": "polyhedron_skin.safetensors",
  "type": "lora",
  "tags": ["skin", "realism"],
  "compatible_with": ["SD 1.5"],
  "recommended_strength": 0.8,
  "description": "Detailed skin texture"
}
```

### `suggest_model(task, style, subject)`

Recommend the best model for a task.

**Parameters:**
- `task` (str): Task type (e.g., "portrait", "landscape", "anime", "video")
- `style` (str, optional): Style preference
- `subject` (str, optional): Subject matter

**Returns:**
```json
{
  "status": "success",
  "model": "sd15",
  "reason": "Best for portrait photography with high detail",
  "alternatives": ["sdxl"]
}
```

### `suggest_loras(prompt, model, max_suggestions)`

Recommend LoRAs based on prompt content.

**Parameters:**
- `prompt` (str): Generation prompt
- `model` (str): Model being used
- `max_suggestions` (int): Maximum suggestions (default: 3)

**Returns:**
```json
{
  "status": "success",
  "suggestions": [
    {
      "name": "polyhedron_skin.safetensors",
      "strength": 0.8,
      "reason": "Enhances skin texture detail"
    }
  ],
  "count": 1
}
```

---

## Gallery & History Tools

### `list_images(limit, prefix, sort)`

Browse generated images from MinIO storage.

**Parameters:**
- `limit` (int): Maximum images to return (default: 20)
- `prefix` (str): Filter by filename prefix (optional)
- `sort` (str): Sort order - "newest", "oldest", "name" (default: "newest")

**Returns:**
```json
{
  "status": "success",
  "images": [
    {
      "filename": "20240815_143045_sunset.png",
      "url": "http://192.168.1.215:9000/comfy-gen/20240815_143045_sunset.png",
      "size": 2048576,
      "modified": "2024-08-15T14:30:45"
    }
  ],
  "count": 1
}
```

### `get_image_info(filename)`

Get metadata for a specific image.

### `delete_image(filename)`

Delete an image from storage.

### `get_history(limit)`

View generation history with prompts and parameters.

---

## Prompt Engineering Tools

### `build_prompt(subject, style, setting)`

Construct a well-formed prompt from components.

**Parameters:**
- `subject` (str): Main subject of the image
- `style` (str, optional): Art style or aesthetic
- `setting` (str, optional): Scene or environment

**Returns:**
```json
{
  "status": "success",
  "prompt": "a majestic dragon, fantasy art style, in a mountain landscape with volumetric lighting"
}
```

### `suggest_negative(model_type)`

Get recommended negative prompt for model type.

**Parameters:**
- `model_type` (str): Model type - "sd15", "sdxl", "flux", "wan" (default: "sd15")

**Returns:**
```json
{
  "status": "success",
  "negative_prompt": "blurry, low quality, watermark, text, cropped, worst quality, low quality, jpeg artifacts"
}
```

### `analyze_prompt(prompt)`

Analyze prompt and suggest improvements.

**Parameters:**
- `prompt` (str): Prompt to analyze

**Returns:**
```json
{
  "status": "success",
  "issues": ["Too short", "Missing style descriptors"],
  "suggestions": ["Add more detail", "Specify art style"],
  "improved_prompt": "a majestic dragon perched on a cliff, detailed scales, epic fantasy art, dramatic lighting, 8k, trending on artstation"
}
```

---

## Progress & Control Tools

### `get_progress(prompt_id)`

Get current generation progress.

**Parameters:**
- `prompt_id` (str, optional): Specific prompt ID to check (checks current if not provided)

**Returns:**
```json
{
  "status": "success",
  "progress": {
    "current_step": 15,
    "max_steps": 20,
    "percent": 75
  }
}
```

### `cancel(prompt_id)`

Cancel current or specific generation job.

### `get_queue()`

View queued jobs.

### `get_system_status()`

Get GPU/VRAM/server health information.

---

## Service Management Tools

### `start_comfyui_service()`

Start the ComfyUI server on moira.

### `stop_comfyui_service()`

Stop the ComfyUI server.

### `restart_comfyui_service()`

Restart the ComfyUI server.

### `check_comfyui_service_status()`

Check if ComfyUI server is running.

---

## Usage Examples

### Example 1: Discover and Download a HuggingFace Model

```python
# Search for FLUX models
search_result = await hf_search_models(
    query="flux",
    library="diffusers",
    pipeline_tag="text-to-image",
    limit=5
)

# Get detailed info about a model
model_info = await hf_get_model_info("black-forest-labs/FLUX.1-dev")

# List files in the repo
files = await hf_list_files("black-forest-labs/FLUX.1-dev")

# Download a specific file
download_result = await hf_download(
    model_id="black-forest-labs/FLUX.1-dev",
    filename="diffusion_pytorch_model.safetensors",
    local_dir="/path/to/models/checkpoints"
)
```

### Example 2: Find LoRAs on CivitAI

```python
# Search for SD 1.5 LoRAs
loras = await search_civitai(
    query="detailed skin",
    model_type="lora",
    base_model="SD 1.5",
    limit=10
)

# Review results and select one
selected_lora = loras["results"][0]
print(f"Found: {selected_lora['name']}")
print(f"Downloads: {selected_lora['downloads']}")
print(f"Rating: {selected_lora['rating']}")
```

### Example 3: Complete Generation Workflow

```python
# 1. Search for models
models_result = await hf_search_models(query="sdxl", limit=3)

# 2. Get model suggestions
suggestion = await suggest_model(task="portrait", style="photorealistic")

# 3. Get LoRA recommendations
lora_suggestions = await suggest_loras(
    prompt="detailed portrait of a woman",
    model="sd15",
    max_suggestions=3
)

# 4. Build enhanced prompt
prompt_result = await build_prompt(
    subject="a woman with detailed skin",
    style="photorealistic portrait",
    setting="studio lighting"
)

# 5. Generate image
image = await generate_image(
    prompt=prompt_result["prompt"],
    model="sd15",
    preset="high-quality",
    loras=[{"name": "polyhedron_skin.safetensors", "strength": 0.8}],
    output_path="/tmp/portrait.png",
    json_progress=True
)

# 6. Check results
print(f"Image URL: {image['url']}")
print(f"Local path: {image['local_path']}")
```

---

## API Key Configuration

### CivitAI API Key

1. Get your API key from https://civitai.com/user/account
2. Add to your environment:
   ```bash
   echo "CIVITAI_API_KEY=your_key_here" >> .env
   ```
3. Or set in MCP config JSON

### HuggingFace Token

1. Get your token from https://huggingface.co/settings/tokens
2. Add to your environment:
   ```bash
   echo "HF_TOKEN=hf_your_token_here" >> .env
   ```
3. Or set in MCP config JSON

**Note:** HF token is required for:
- Gated models (e.g., FLUX.1-dev)
- Private repositories
- Increased rate limits

---

## Error Handling

All tools return a standardized response format:

**Success:**
```json
{
  "status": "success",
  "...": "..."
}
```

**Error:**
```json
{
  "status": "error",
  "error": "Detailed error message"
}
```

Common errors:
- `"Model not found"` - Invalid model ID
- `"Model is gated"` - Requires HF_TOKEN and accepting terms
- `"Download failed"` - Network issue or invalid file
- `"Server not responding"` - ComfyUI server is down
