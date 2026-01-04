# Comprehensive MCP Server Usage Guide

This guide explains how to use the ComfyUI Comprehensive Generation Server MCP tools.

## Overview

The MCP server provides 25 tools across 7 categories for complete AI-driven image/video generation:

1. **Service Management** - Start/stop/check ComfyUI server
2. **Image Generation** - Generate and transform images
3. **Video Generation** - Create videos from text or images
4. **Model Management** - List, discover, and download models
5. **Gallery & History** - Browse and manage generated content
6. **Prompt Engineering** - Build and analyze prompts
7. **Progress & Control** - Monitor and control generation jobs

## Setup

### VS Code MCP Configuration

Add to `.vscode/settings.json` or your MCP client config:

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
        "CIVITAI_API_KEY": "${CIVITAI_API_KEY}"
      }
    }
  }
}
```

### Environment Variables

- `COMFYUI_HOST` - ComfyUI server URL (default: http://192.168.1.215:8188)
- `MINIO_ENDPOINT` - MinIO endpoint (default: 192.168.1.215:9000)
- `MINIO_BUCKET` - MinIO bucket name (default: comfy-gen)
- `CIVITAI_API_KEY` - Optional CivitAI API key for model downloads

## Tool Categories

### 1. Service Management

**check_comfyui_service_status()**
- Check if ComfyUI server is running
- Returns: Status report with process state and API health

**start_comfyui_service()**
- Start ComfyUI server on moira
- Returns: Success/failure message

**stop_comfyui_service()**
- Stop ComfyUI server
- Returns: Success/failure message

**restart_comfyui_service()**
- Restart ComfyUI server
- Returns: Success/failure message

### 2. Image Generation

**generate_image(prompt, ...)**
- Generate image from text prompt
- Args:
  - `prompt` (str): What to generate
  - `negative_prompt` (str): What to avoid (default: "blurry, low quality, watermark")
  - `model` (str): Model to use - sd15, flux, sdxl (default: sd15)
  - `width` (int): Image width (default: 512)
  - `height` (int): Image height (default: 512)
  - `steps` (int): Sampling steps (default: 20)
  - `cfg` (float): CFG scale (default: 7.0)
  - `sampler` (str): Sampler algorithm (default: euler)
  - `scheduler` (str): Scheduler type (default: normal)
  - `seed` (int): Random seed, -1 for random (default: -1)
- Returns: `{status, url, prompt_id, metadata}`

**img2img(input_image, prompt, ...)**
- Transform existing image with prompt guidance
- Args:
  - `input_image` (str): URL or path to input image
  - `prompt` (str): Transformation prompt
  - `negative_prompt` (str): What to avoid
  - `denoise` (float): Strength 0.0-1.0, lower preserves more original (default: 0.7)
  - `model` (str): Model to use (default: sd15)
  - `steps` (int): Sampling steps (default: 20)
  - `cfg` (float): CFG scale (default: 7.0)
  - `seed` (int): Random seed (default: -1)
- Returns: `{status, url, prompt_id, metadata}`

### 3. Video Generation

**generate_video(prompt, ...)**
- Generate video from text using Wan 2.2 T2V
- Args:
  - `prompt` (str): Video description
  - `negative_prompt` (str): What to avoid (default: "static, blurry, watermark")
  - `width` (int): Video width (default: 832)
  - `height` (int): Video height (default: 480)
  - `frames` (int): Number of frames, ~5sec at 16fps = 81 (default: 81)
  - `fps` (int): Frames per second (default: 16)
  - `steps` (int): Sampling steps (default: 30)
  - `cfg` (float): CFG scale (default: 6.0)
  - `seed` (int): Random seed (default: -1)
- Returns: `{status, url, prompt_id, metadata}`

**image_to_video(input_image, prompt, ...)**
- Animate image to video using Wan 2.2 I2V
- Args:
  - `input_image` (str): URL or path to input image
  - `prompt` (str): Motion description
  - `negative_prompt` (str): What to avoid
  - `motion_strength` (float): Movement amount 0.0-1.0+ (default: 1.0)
  - `frames` (int): Number of frames (default: 81)
  - `fps` (int): Frames per second (default: 16)
  - `steps` (int): Sampling steps (default: 30)
  - `seed` (int): Random seed (default: -1)
- Returns: `{status, url, prompt_id, metadata}`

### 4. Model Management

**list_models()**
- List installed checkpoint models
- Returns: `{status, checkpoints, diffusion_models, vae, count}`

**list_loras()**
- List installed LoRAs with compatibility info
- Returns: `{status, loras: [{name, tags, compatible_with, recommended_strength, description}], count}`

**get_model_info(model_name)**
- Get detailed metadata about a model
- Returns: `{status, name, type, ...metadata}`

**suggest_model(task, style=None, subject=None)**
- Recommend best model for a task
- Args:
  - `task` (str): portrait, landscape, anime, video, text-to-video, image-to-video
  - `style` (str): Optional style preference
  - `subject` (str): Optional subject matter
- Returns: `{status, recommended, alternatives, reason}`

**suggest_loras(prompt, model, max_suggestions=3)**
- Recommend LoRAs based on prompt and model
- Args:
  - `prompt` (str): Generation prompt
  - `model` (str): Model being used
  - `max_suggestions` (int): Max suggestions (default: 3)
- Returns: `{status, suggestions: [{name, suggested_strength, reason}], count}`

**search_civitai(query, model_type="all", ...)**
- Search CivitAI for models and LoRAs
- Args:
  - `query` (str): Search query
  - `model_type` (str): all, checkpoint, lora, vae (default: all)
  - `base_model` (str): Filter by base model (SD 1.5, SDXL, etc.)
  - `sort` (str): Most Downloaded, Highest Rated, Newest (default: Most Downloaded)
  - `nsfw` (bool): Include NSFW results (default: True)
  - `limit` (int): Max results (default: 10)
- Returns: `{status, results: [{id, name, type, downloads, rating, preview_url, download_url}], count}`

### 5. Gallery & History

**list_images(limit=20, prefix="", sort="newest")**
- Browse generated images from storage
- Args:
  - `limit` (int): Max images to return (default: 20)
  - `prefix` (str): Filter by filename prefix
  - `sort` (str): newest, oldest, name (default: newest)
- Returns: `{status, images: [{name, size, last_modified, url}], count}`

**get_image_info(image_name)**
- Get generation parameters for an image
- Returns: `{status, name, url, size, last_modified, generation_params}`

**delete_image(image_name)**
- Remove image from storage
- Returns: `{status, message}`

**get_history(limit=10)**
- Get recent generations with full parameters
- Returns: `{status, history: [{prompt_id, outputs, status, parameters}], count}`

### 6. Prompt Engineering

**build_prompt(subject, style=None, setting=None)**
- Construct a well-formed prompt
- Args:
  - `subject` (str): Main subject
  - `style` (str): Art style or aesthetic
  - `setting` (str): Scene or environment
- Returns: `{status, prompt, components}`

**suggest_negative(model_type="sd15")**
- Get recommended negative prompt for model
- Args:
  - `model_type` (str): sd15, sdxl, flux, wan (default: sd15)
- Returns: `{status, default, suggestions, model_type}`

**analyze_prompt(prompt)**
- Analyze prompt and suggest improvements
- Returns: `{status, analysis: {length, word_count, issues, suggestions, detected_elements}, prompt}`

### 7. Progress & Control

**get_progress(prompt_id=None)**
- Get current generation progress
- Args:
  - `prompt_id` (str): Optional specific prompt ID to check
- Returns: `{status, current_job, queue_length, is_processing}` or `{status, prompt_id, position}`

**cancel(prompt_id=None)**
- Cancel current or specific generation
- Args:
  - `prompt_id` (str): Optional prompt to cancel (cancels current if not provided)
- Returns: `{status, message}`

**get_queue()**
- View queued jobs
- Returns: `{status, running: [...], pending: [...], running_count, pending_count}`

**get_system_status()**
- Get GPU/VRAM/server health info
- Returns: `{status, system, devices, gpu: [{name, type, vram_total, vram_free, vram_used_percent}]}`

## Usage Examples

### Example 1: Simple Image Generation

```python
# Agent workflow:
result = await generate_image(
    prompt="a sunset over mountains, highly detailed, 8k",
    width=768,
    height=512,
    steps=25
)
# Result: {"status": "success", "url": "http://192.168.1.215:9000/comfy-gen/20260104_123456_output.png", ...}
```

### Example 2: Intelligent Model Selection

```python
# 1. Ask for model recommendation
model_suggestion = await suggest_model(task="portrait", style="realistic")
# Returns: {"recommended": "v1-5-pruned-emaonly-fp16.safetensors", ...}

# 2. Get LoRA suggestions
lora_suggestions = await suggest_loras(
    prompt="woman portrait with detailed face",
    model=model_suggestion["recommended"]
)
# Returns: {"suggestions": [{"name": "detail_enhancer.safetensors", "suggested_strength": 0.8}]}

# 3. Generate with suggestions
result = await generate_image(
    prompt="woman portrait with detailed face, professional lighting",
    model=model_suggestion["recommended"]
)
```

### Example 3: Animated Portrait Creation

```python
# 1. Generate base image
image_result = await generate_image(
    prompt="woman portrait, professional photo, detailed face",
    width=832,
    height=480
)

# 2. Get LoRA suggestions for video
loras = await suggest_loras(
    prompt="subtle head turn, natural movement",
    model="wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
)

# 3. Animate to video
video_result = await image_to_video(
    input_image=image_result["url"],
    prompt="subtle head turn, slight smile",
    steps=30
)
# Result: {"status": "success", "url": "http://192.168.1.215:9000/comfy-gen/video_20260104_123456.mp4"}
```

### Example 4: Model Discovery

```python
# Search CivitAI for car detail LoRAs
results = await search_civitai(
    query="car detail lora",
    model_type="lora",
    base_model="SD 1.5",
    limit=5
)

# Browse results
for model in results["results"]:
    print(f"{model['name']} - {model['downloads']} downloads")
```

### Example 5: Gallery Management

```python
# List recent images
images = await list_images(limit=10, sort="newest")

# Get generation details for specific image
info = await get_image_info(images["images"][0]["name"])
print(f"Generated with prompt: {info['generation_params']['positive_prompt']}")

# Delete old images
await delete_image("old_image.png")
```

## Tips for AI Agents

1. **Always check system status** before large batch jobs
2. **Use suggest_model** to pick the right model for the task
3. **Use suggest_loras** to enhance generation quality
4. **Monitor progress** with get_progress for long-running generations
5. **Browse history** to learn from successful generations
6. **Analyze prompts** before generation to catch issues early

## Error Handling

All tools return a `status` field:
- `"success"` - Operation completed successfully
- `"error"` - Operation failed (see `error` field for details)
- `"running"` / `"pending"` / `"completed"` - For progress queries

Always check the `status` field before using other fields in the response.

## Architecture

```
comfygen/
├── __init__.py          # Package exports
├── comfyui_client.py    # ComfyUI API wrapper
├── minio_client.py      # MinIO storage wrapper
├── civitai_client.py    # CivitAI API wrapper
├── workflows.py         # Workflow manipulation
├── models.py            # Model registry & recommendations
└── tools/               # MCP tool implementations
    ├── generation.py    # Image generation tools
    ├── video.py         # Video generation tools
    ├── models.py        # Model management tools
    ├── gallery.py       # Gallery & history tools
    ├── prompts.py       # Prompt engineering tools
    └── control.py       # Progress & control tools
```

## Limitations

Current implementation includes:
- ✅ Full text-to-image generation
- ✅ Image-to-image transformation
- ✅ Text-to-video (Wan 2.2)
- ✅ Image-to-video (Wan 2.2)
- ✅ Model discovery and suggestions
- ✅ Gallery and history management
- ⏳ Inpainting (workflow pending)
- ⏳ Upscaling (workflow pending)
- ⏳ Face restoration (workflow pending)
- ⏳ Model downloads from CivitAI (requires moira access)

## Support

See also:
- `docs/AGENT_GUIDE.md` - Detailed guide for AI agents
- `docs/MODEL_REGISTRY.md` - Available models and LoRAs
- `docs/API_REFERENCE.md` - Internal API documentation
