# MCP Servers Documentation

**Last verified:** 2026-01-05

This document describes all MCP (Model Context Protocol) servers available in comfy-gen and their exposed tools.

## Overview

comfy-gen provides three MCP servers:

1. **comfy-gen** (`mcp_server.py`) - Main server for ComfyUI image/video generation
2. **civitai** (`mcp_servers/civitai_mcp.py`) - CivitAI model discovery and verification
3. **huggingface** (`mcp_servers/huggingface_mcp.py`) - HuggingFace Hub model discovery and download

## Configuration

MCP servers are configured in `mcp_config.json`. Each server requires specific environment variables:

```json
{
  "mcpServers": {
    "comfy-gen": {
      "command": ".venv/bin/python3",
      "args": ["mcp_server.py"],
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000",
        "MINIO_BUCKET": "comfy-gen"
      }
    },
    "civitai": {
      "command": ".venv/bin/python3",
      "args": ["mcp_servers/civitai_mcp.py"],
      "env": {
        "CIVITAI_API_KEY": "${CIVITAI_API_KEY}"
      }
    },
    "huggingface": {
      "command": ".venv/bin/python3",
      "args": ["mcp_servers/huggingface_mcp.py"],
      "env": {
        "HF_TOKEN": "${HF_TOKEN}"
      }
    }
  }
}
```

## Server 1: comfy-gen (Main Generation Server)

**File:** `mcp_server.py`

**Purpose:** Comprehensive image/video generation, model management, and ComfyUI service control.

### Service Management Tools

#### `start_comfyui_service()`
Start the ComfyUI server on moira.

**Returns:** Status message

#### `stop_comfyui_service()`
Stop the ComfyUI server on moira.

**Returns:** Status message

#### `restart_comfyui_service()`
Restart the ComfyUI server (useful for applying config changes).

**Returns:** Status message

#### `check_comfyui_service_status()`
Check if ComfyUI is running and responding.

**Returns:** Status report with process state and API health

### Image Generation Tools

#### `generate_image(prompt, negative_prompt, model, width, height, steps, cfg, sampler, scheduler, seed, preset, lora_preset, output_path, json_progress, validate, auto_retry, retry_limit, positive_threshold)`
Generate image from text prompt with CLIP validation.

**Key Parameters:**
- `prompt` (str): Positive text prompt
- `negative_prompt` (str, optional): What to avoid (uses default from presets.yaml if None)
- `model` (str): Model to use (sd15, flux, sdxl)
- `width`, `height` (int): Output dimensions
- `steps` (int): Sampling steps
- `cfg` (float): CFG scale
- `preset` (str): Generation preset (draft, balanced, high-quality, fast, ultra)
- `lora_preset` (str): LoRA preset from lora_catalog.yaml
- `validate` (bool): Run CLIP validation
- `auto_retry` (bool): Retry if validation fails

**Returns:** Dictionary with status, url, validation results

#### `img2img(input_image, prompt, negative_prompt, denoise, model, steps, cfg, seed)`
Transform existing image with prompt guidance.

**Returns:** Dictionary with status and url

### Video Generation Tools

#### `generate_video(prompt, negative_prompt, width, height, frames, fps, steps, cfg, seed)`
Generate video from text using Wan 2.2 T2V.

**Returns:** Dictionary with status and url

#### `image_to_video(input_image, prompt, negative_prompt, motion_strength, frames, fps, steps, seed)`
Animate image to video using Wan 2.2 I2V.

**Returns:** Dictionary with status and url

### Model Management Tools

#### `list_models()`
List all installed checkpoint models.

**Returns:** Dictionary with checkpoints, diffusion_models, vae arrays

#### `list_loras()`
List all installed LoRAs with compatibility info from catalog.

**Returns:** Dictionary with enriched LoRA metadata

#### `get_model_info(model_name)`
Get detailed metadata about a specific model.

**Returns:** Dictionary with model type and catalog info

#### `suggest_model(task, style, subject)`
Recommend best model for a task.

**Parameters:**
- `task`: portrait, landscape, anime, video, etc.
- `style`: Optional style preference
- `subject`: Optional subject matter

#### `suggest_loras(prompt, model, max_suggestions)`
Recommend LoRAs based on prompt content.

**Returns:** Dictionary with LoRA suggestions

#### `search_civitai(query, model_type, base_model, sort, nsfw, limit)`
Search CivitAI for models (wrapper for civitai server).

**Returns:** Dictionary with search results

### Gallery & History Tools

#### `list_images(limit, prefix, sort)`
Browse generated images from MinIO storage.

**Returns:** Dictionary with image list

#### `get_image_info(image_name)`
Get generation parameters and metadata for an image.

**Returns:** Dictionary with metadata

#### `delete_image(image_name)`
Remove image from storage.

**Returns:** Dictionary with deletion status

#### `get_history(limit)`
Get recent generations with full parameters.

**Returns:** Dictionary with generation history

### Prompt Engineering Tools

#### `build_prompt(subject, style, setting)`
Construct well-formed prompt from components.

**Returns:** Dictionary with constructed prompt

#### `suggest_negative(model_type)`
Get recommended negative prompt for model type.

**Returns:** Dictionary with negative prompt suggestions

#### `analyze_prompt(prompt)`
Analyze prompt and suggest improvements.

**Returns:** Dictionary with analysis and suggestions

### Progress & Control Tools

#### `get_progress(prompt_id)`
Get current generation progress.

**Returns:** Dictionary with progress information

#### `cancel(prompt_id)`
Cancel current or specific generation job.

**Returns:** Dictionary with cancellation status

#### `get_queue()`
View queued jobs.

**Returns:** Dictionary with queue information

#### `get_system_status()`
Get GPU/VRAM/server health information.

**Returns:** Dictionary with system status

#### `validate_workflow(model, prompt, width, height)`
Validate workflow without generating (dry run).

**Returns:** Dictionary with validation results

## Server 2: civitai (Model Discovery Server)

**File:** `mcp_servers/civitai_mcp.py`

**Purpose:** Agent-assisted model discovery, verification, and metadata lookup from CivitAI.

**Authentication:** Requires `CIVITAI_API_KEY` environment variable for:
- NSFW content access
- Authenticated downloads
- Higher rate limits

### CivitAI Tools

#### `civitai_search_models(query, model_type, base_model, sort, nsfw, limit)`
Search CivitAI for models by query with filters.

**Parameters:**
- `query` (str): Search query (e.g., "battleship", "anime style")
- `model_type` (str, optional): Filter by type - Checkpoint, LORA, VAE
- `base_model` (str, optional): Filter by base model - "SD 1.5", "SDXL", "Flux.1 D"
- `sort` (str): "Most Downloaded" (default), "Highest Rated", "Newest"
- `nsfw` (bool): Include NSFW results (default: True)
- `limit` (int): Max results (default: 10, max: 100)

**Returns:**
```python
{
  "status": "success",
  "results": [
    {
      "id": 12345,
      "name": "Model Name",
      "type": "LORA",
      "description": "Brief description...",
      "creator": "username",
      "downloads": 50000,
      "rating": 4.8,
      "base_model": "SD 1.5",
      "version_id": 67890,
      "version_name": "v1.0",
      "preview_url": "https://...",
      "download_url": "https://...",
      "nsfw": false
    }
  ],
  "count": 1,
  "query": "battleship"
}
```

#### `civitai_get_model(model_id)`
Get detailed information about a specific CivitAI model.

**Parameters:**
- `model_id` (int): CivitAI model ID

**Returns:** Full model details including all versions, tags, stats

**Example:**
```python
result = await civitai_get_model(4384)
model = result["model"]
print(f"Model: {model['name']}")
print(f"Type: {model['type']}")
print(f"Versions: {len(model['modelVersions'])}")
```

#### `civitai_lookup_hash(file_hash)` ⭐ CRITICAL FEATURE
Look up model version by SHA256 file hash - the AUTHORITATIVE way to verify LoRA compatibility.

**Purpose:** Identify what base model a LoRA or checkpoint is designed for without guessing.

**Parameters:**
- `file_hash` (str): SHA256 hash of .safetensors file (64 hex characters)

**Workflow:**
```bash
# 1. Get hash from moira
ssh moira "powershell -Command \"(Get-FileHash -Algorithm SHA256 'C:\Users\jrjen\comfy\models\loras\some_lora.safetensors').Hash\""

# 2. Look up on CivitAI via MCP tool
result = await civitai_lookup_hash("abc123...")

# 3. Check base model
if result["status"] == "success":
    base_model = result["base_model"]
    # "SD 1.5" = Use for image generation
    # "Wan Video 14B t2v" = Video only, DO NOT use for images
    # "SDXL" = Use with SDXL model
```

**Returns:**
```python
{
  "status": "success",
  "model_name": "Erect Penis LoRA",
  "model_id": 123456,
  "version_id": 789012,
  "version_name": "epoch_80",
  "base_model": "Wan Video 14B t2v",  # CRITICAL - tells you compatibility
  "trained_words": ["erect_penis", "close_up"],
  "download_url": "https://...",
  "files": [...]
}
```

**Use Cases:**
- Verify LoRA compatibility before use (SD 1.5 vs Wan Video vs SDXL)
- Update `lora_catalog.yaml` with CivitAI-verified metadata
- Audit existing LoRA collection for misclassified files
- Prevent mixing incompatible LoRAs (e.g., video LoRA on image model)

**Error Handling:**
```python
result = await civitai_lookup_hash(hash_value)
if result["status"] == "error":
    if "Not found" in result["error"]:
        # LoRA not on CivitAI (custom or private)
        print("LoRA not in CivitAI database")
    else:
        # Network or API error
        print(f"Lookup failed: {result['error']}")
```

#### `civitai_get_download_url(model_id, version_id)`
Get authenticated download URL for a CivitAI model.

**Parameters:**
- `model_id` (int): CivitAI model ID
- `version_id` (int, optional): Specific version (uses latest if not provided)

**Returns:**
```python
{
  "status": "success",
  "download_url": "https://civitai.com/api/download/models/123?token=...",
  "model_id": 12345,
  "version_id": 67890,
  "requires_auth": true  # Whether CIVITAI_API_KEY is needed
}
```

**Note:** Download URL may include temporary authentication token. NSFW models always require API key.

## Server 3: huggingface (HuggingFace Hub Discovery Server)

**File:** `mcp_servers/huggingface_mcp.py`

**Purpose:** Agent-assisted model discovery, metadata lookup, and downloads from HuggingFace Hub.

**Authentication:** Requires `HF_TOKEN` environment variable for:
- Gated models (models requiring terms acceptance)
- Higher rate limits
- Private repositories

### HuggingFace Hub Tools

#### `hf_search_models(query, library, tags, pipeline_tag, sort, limit)`
Search HuggingFace Hub for models by query with filters.

**Parameters:**
- `query` (str, optional): Search query (e.g., "stable diffusion", "flux", "text encoder")
- `library` (str, optional): Filter by library - "diffusers", "transformers", etc.
- `tags` (str, optional): Comma-separated tags to filter by (e.g., "text-to-image,sdxl")
- `pipeline_tag` (str, optional): Filter by pipeline tag - "text-to-image", "image-to-image", etc.
- `sort` (str): "downloads" (default), "likes", "created", "modified"
- `limit` (int): Max results (default: 10, max: 100)

**Returns:**
```python
{
  "status": "success",
  "results": [
    {
      "id": "stabilityai/stable-diffusion-xl-base-1.0",
      "author": "stabilityai",
      "name": "stable-diffusion-xl-base-1.0",
      "downloads": 5000000,
      "likes": 12000,
      "tags": ["text-to-image", "sdxl", "diffusers"],
      "pipeline_tag": "text-to-image",
      "library": "diffusers",
      "created_at": "2023-07-26T15:00:00.000Z",
      "last_modified": "2024-01-15T10:30:00.000Z"
    }
  ],
  "count": 1,
  "query": "stable diffusion"
}
```

**Example Usage:**
```python
# Search for SDXL models
result = await hf_search_models(
    query="stable diffusion",
    library="diffusers",
    tags="text-to-image,sdxl",
    sort="downloads",
    limit=10
)

# Search for text encoders
result = await hf_search_models(
    query="t5 encoder",
    library="transformers",
    limit=5
)

# Search for Flux models
result = await hf_search_models(
    query="flux",
    pipeline_tag="text-to-image",
    sort="likes"
)
```

#### `hf_get_model_info(model_id)`
Get detailed information about a specific HuggingFace model.

**Parameters:**
- `model_id` (str): HuggingFace model ID (e.g., "stabilityai/stable-diffusion-xl-base-1.0")

**Returns:**
```python
{
  "status": "success",
  "model": {
    "id": "stabilityai/stable-diffusion-xl-base-1.0",
    "author": "stabilityai",
    "name": "stable-diffusion-xl-base-1.0",
    "downloads": 5000000,
    "likes": 12000,
    "tags": ["text-to-image", "sdxl", "diffusers"],
    "pipeline_tag": "text-to-image",
    "library": "diffusers",
    "created_at": "2023-07-26T15:00:00.000Z",
    "last_modified": "2024-01-15T10:30:00.000Z",
    "card_data": {
      "license": "openrail++",
      "tags": ["text-to-image", "stable-diffusion"]
    },
    "sha": "abc123...",
    "siblings": [
      {"filename": "model_index.json", "size": 543},
      {"filename": "unet/diffusion_pytorch_model.safetensors", "size": 5135000000}
    ],
    "gated": false
  }
}
```

**Example:**
```python
result = await hf_get_model_info("stabilityai/stable-diffusion-xl-base-1.0")
model = result["model"]
print(f"Model: {model['id']}")
print(f"Downloads: {model['downloads']}")
print(f"Files: {len(model['siblings'])}")
if model["gated"]:
    print("[WARN] This model requires accepting terms on HuggingFace")
```

#### `hf_list_files(model_id)`
List all files in a HuggingFace model repository.

**Parameters:**
- `model_id` (str): HuggingFace model ID

**Returns:**
```python
{
  "status": "success",
  "files": [
    {"filename": "config.json", "size": 543},
    {"filename": "model.safetensors", "size": 5135000000},
    {"filename": "README.md", "size": 1234}
  ],
  "count": 3
}
```

**Example:**
```python
result = await hf_list_files("stabilityai/stable-diffusion-xl-base-1.0")
for file in result["files"]:
    size_mb = file["size"] / (1024 * 1024)
    print(f"{file['filename']}: {size_mb:.2f} MB")
```

#### `hf_download(model_id, filename, local_dir)`
Download a specific file from a HuggingFace model repository.

**Parameters:**
- `model_id` (str): HuggingFace model ID
- `filename` (str): File to download (e.g., "model.safetensors", "config.json")
- `local_dir` (str): Local directory to save file (default: /tmp)

**Returns:**
```python
{
  "status": "success",
  "path": "/tmp/model.safetensors",
  "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
  "filename": "model.safetensors"
}
```

**Example:**
```python
# Download a text encoder
result = await hf_download(
    model_id="openai/clip-vit-large-patch14",
    filename="pytorch_model.bin",
    local_dir="/tmp"
)

if result["status"] == "success":
    print(f"Downloaded to: {result['path']}")
    # Transfer to moira if needed
    # scp {result['path']} moira:C:\\Users\\jrjen\\comfy\\models\\text_encoders\\
```

**Notes:**
- Gated models require `HF_TOKEN` environment variable
- Some models require accepting terms on HuggingFace website before download
- Downloads are cached in HuggingFace cache directory (`~/.cache/huggingface/`)
- Use SSH/SCP to transfer files to moira models directory after download

## Rate Limiting

**HuggingFace Hub API:**
- Without token: ~1000 requests/hour
- With token: Higher limits (not publicly documented)
- Be conservative with batch operations
- Add delays between requests (0.5-1 second recommended)

**CivitAI API:**
- Without API key: ~100 requests/hour
- With API key: ~1000 requests/hour
- Be conservative with batch operations
- Add delays between requests (0.5-1 second recommended)

**ComfyUI API:**
- No strict rate limit (local network)
- Queue system handles concurrent requests
- Monitor with `get_system_status()` for VRAM availability

## Error Handling

All tools return dictionaries with consistent structure:

**Success:**
```python
{
  "status": "success",
  "results": [...],
  # ... tool-specific data
}
```

**Error:**
```python
{
  "status": "error",
  "error": "Error message description"
}
```

## Example Workflows

### Workflow 1: Verify LoRA Compatibility

```python
# 1. Get hash of local LoRA file
import subprocess
result = subprocess.run(
    ['ssh', 'moira', 'powershell', '-Command', 
     "(Get-FileHash -Algorithm SHA256 'C:\\Users\\jrjen\\comfy\\models\\loras\\mystery_lora.safetensors').Hash"],
    capture_output=True, text=True
)
file_hash = result.stdout.strip()

# 2. Look up on CivitAI
lookup_result = await civitai_lookup_hash(file_hash)

# 3. Check compatibility
if lookup_result["status"] == "success":
    base_model = lookup_result["base_model"]
    if "SD 1.5" in base_model:
        print("[OK] Compatible with SD 1.5 image generation")
    elif "Wan Video" in base_model:
        print("[WARN] Video-only LoRA - DO NOT use for images")
    elif "SDXL" in base_model:
        print("[OK] Compatible with SDXL")
else:
    print(f"[ERROR] {lookup_result['error']}")
```

### Workflow 2: Search and Download Model

```python
# 1. Search for models
search_result = await civitai_search_models(
    query="realistic portraits",
    model_type="Checkpoint",
    base_model="SD 1.5",
    limit=5
)

# 2. Pick a model
if search_result["status"] == "success":
    model = search_result["results"][0]
    print(f"Found: {model['name']} by {model['creator']}")
    
    # 3. Get download URL
    download_result = await civitai_get_download_url(model["id"])
    
    if download_result["status"] == "success":
        print(f"Download URL: {download_result['download_url']}")
        # Now use this URL to download to moira
```

### Workflow 3: Generate Image with Validated LoRA

```python
# 1. Verify LoRA is SD 1.5 compatible
lora_hash = "abc123..."  # Get from moira
lookup = await civitai_lookup_hash(lora_hash)

if "SD 1.5" in lookup.get("base_model", ""):
    # 2. Generate with verified LoRA
    result = await generate_image(
        prompt="beautiful portrait",
        model="sd15",
        lora_preset="portrait_realism",  # Preset includes this LoRA
        steps=50,
        cfg=8.0
    )
    
    print(f"Generated: {result['url']}")
else:
    print("[ERROR] LoRA not compatible with SD 1.5")
```

### Workflow 4: Download Model from HuggingFace Hub

```python
# 1. Search for a specific model
search_result = await hf_search_models(
    query="flux",
    library="diffusers",
    pipeline_tag="text-to-image",
    limit=5
)

# 2. Get detailed info about the model
if search_result["status"] == "success" and search_result["count"] > 0:
    model_id = search_result["results"][0]["id"]
    info_result = await hf_get_model_info(model_id)
    
    # 3. List files to find what we need
    files_result = await hf_list_files(model_id)
    
    # 4. Download specific file
    for file in files_result["files"]:
        if file["filename"].endswith(".safetensors"):
            download_result = await hf_download(
                model_id=model_id,
                filename=file["filename"],
                local_dir="/tmp"
            )
            
            if download_result["status"] == "success":
                print(f"Downloaded: {download_result['path']}")
                # Now transfer to moira models directory
```

## Testing MCP Servers

### Test comfy-gen Server
```bash
python3 tests/test_mcp_server.py
```

### Test civitai Server
```bash
python3 tests/test_civitai_mcp.py
```

### Test huggingface Server
```bash
python3 tests/test_huggingface_mcp.py
```

### List Available Tools
```bash
# For comfy-gen server
python3 -c "import asyncio; from mcp_server import mcp; asyncio.run(mcp.list_tools())"

# For civitai server
python3 -c "import asyncio; from mcp_servers.civitai_mcp import mcp; asyncio.run(mcp.list_tools())"

# For huggingface server
python3 -c "import asyncio; from mcp_servers.huggingface_mcp import mcp; asyncio.run(mcp.list_tools())"
```

## Integration with VS Code / Claude Desktop

Add servers to your MCP client configuration (e.g., Claude Desktop config):

```json
{
  "mcpServers": {
    "comfy-gen": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/comfy-gen/mcp_server.py"],
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000",
        "MINIO_BUCKET": "comfy-gen"
      }
    },
    "civitai": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/comfy-gen/mcp_servers/civitai_mcp.py"],
      "env": {
        "CIVITAI_API_KEY": "your-api-key-here"
      }
    },
    "huggingface": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/comfy-gen/mcp_servers/huggingface_mcp.py"],
      "env": {
        "HF_TOKEN": "your-hf-token-here"
      }
    }
  }
}
```

## Security Notes

- **CIVITAI_API_KEY**: Store in `.env` file (gitignored), never commit to repo
- **HF_TOKEN**: Store in `.env` file (gitignored), never commit to repo
- **Download URLs**: May contain temporary tokens, do not log or persist
- **NSFW Content**: Requires API key, use responsibly
- **Rate Limiting**: Respect CivitAI's rate limits to avoid IP bans

## Troubleshooting

### CivitAI server not starting
- Check `CIVITAI_API_KEY` is set in environment
- Verify internet connectivity
- Check Python version (3.10+ required)

### HuggingFace server not starting
- Check `HF_TOKEN` is set in environment (optional but recommended)
- Verify internet connectivity
- Check Python version (3.10+ required)
- Ensure `huggingface_hub` package is installed

### Hash lookup returns "Not found"
- Verify hash is exactly 64 hex characters
- Some models may not be on CivitAI (custom/private)
- Check hash was computed for correct file

### Download requires authentication
- NSFW models (CivitAI) always require API key
- Set `CIVITAI_API_KEY` environment variable
- Get API key from https://civitai.com/user/account
- Gated models (HuggingFace) require HF_TOKEN
- Set `HF_TOKEN` environment variable
- Get token from https://huggingface.co/settings/tokens
- Some models require accepting terms on HuggingFace website first

### HuggingFace download fails
- Check if model is gated (requires token)
- Verify you've accepted terms on HuggingFace website for gated models
- Check filename exists in repository with `hf_list_files`
- Ensure you have sufficient disk space

## See Also

- [USAGE.md](USAGE.md) - CLI usage and examples
- [LORA_GUIDE.md](LORA_GUIDE.md) - LoRA selection guide
- [MODEL_REGISTRY.md](MODEL_REGISTRY.md) - Installed model inventory
- [API_REFERENCE.md](API_REFERENCE.md) - ComfyUI API reference

---

**Documentation Policy:** This is an authoritative reference document. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only.
