# ComfyGen Architecture

**Last verified:** 2026-01-06

System design documentation covering workflows, presets, LoRA injection, and metadata tracking.

## Table of Contents

- [System Overview](#system-overview)
- [Workflows](#workflows)
- [Generation Presets](#generation-presets)
- [Dynamic LoRA Injection](#dynamic-lora-injection)
- [Metadata Tracking](#metadata-tracking)
- [MinIO Object Storage](#minio-object-storage)

---

## System Overview

```
┌──────────────┐      ┌───────────┐      ┌─────────────┐      ┌──────────────────────┐
│   magneto    │─────▶│  GitHub   │─────▶│   ant-man   │─────▶│   moira (ComfyUI)    │
│ (dev machine)│ push │(workflows)│ CI/CD│  (runner)   │ exec │   + RTX 5090 GPU     │
└──────────────┘      └───────────┘      └─────────────┘      └──────────┬───────────┘
                                                                           │
                                                                           ▼
                                                               ┌─────────────────────┐
                                                               │  MinIO Storage      │
                                                               │  192.168.1.215:9000 │
                                                               └─────────────────────┘
```

**Infrastructure:**

| Machine | Role | IP |
|---------|------|-----|
| magneto | Development workstation | 192.168.1.124 |
| moira | ComfyUI server + MinIO + GPU (RTX 5090) | 192.168.1.215 |
| ant-man | GitHub Actions runner (ARM64) | 192.168.1.253 |

**Data Flow:**
1. User runs `generate.py` on magneto (or CI on ant-man)
2. Workflow JSON is sent to ComfyUI API on moira
3. ComfyUI generates image/video using RTX 5090
4. Output is saved locally and uploaded to MinIO
5. Public URL returned to user

---

## Workflows

Workflows are JSON files that define the ComfyUI node graph for generation. Each workflow specifies models, prompts, sampling parameters, and output configuration.

### Workflow Metadata

Each workflow JSON includes a `_workflow_metadata` object at the root level:

| Field | Description |
|-------|-------------|
| `workflow_name` | Human-readable workflow name |
| `description` | What this workflow does |
| `model` | Primary checkpoint model filename |
| `input_requirements` | Any special input requirements (e.g., input image) |
| `output_resolution` | Expected output dimensions |
| `use_case` | When to use this workflow |
| `estimated_time` | Approximate generation time on RTX 5090 |
| `nodes` | Brief description of key nodes |

**Example metadata:**
```json
{
  "_workflow_metadata": {
    "workflow_name": "SD 1.5 Basic Generation",
    "description": "Simple text-to-image generation using Stable Diffusion 1.5",
    "model": "v1-5-pruned-emaonly-fp16.safetensors",
    "output_resolution": "512x512",
    "use_case": "Fast general-purpose image generation",
    "estimated_time": "10-15 seconds on RTX 5090"
  }
}
```

### Available Workflows

#### flux-dev.json (SD 1.5 Text-to-Image)

**Type:** Text-to-Image  
**Model:** v1-5-pruned-emaonly-fp16.safetensors

**Description:**  
Simple text-to-image generation using Stable Diffusion 1.5. Fast and reliable for general-purpose image generation.

**Usage:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a mountain landscape at sunset" \
    --negative-prompt "blurry, low quality" \
    --output /tmp/landscape.png
```

**Parameters:**
- Output: 512x512 PNG
- Steps: 30 (default)
- Sampler: dpmpp_2m
- CFG: 7.0
- Generation time: 10-15 seconds

**Key Nodes:**
1. Checkpoint Loader - Loads SD 1.5 model
2. Positive/Negative Prompts - Text description
3. Empty Latent - Creates 512x512 blank latent
4. KSampler - Diffusion sampling
5. VAE Decode - Converts latent to pixels
6. Save Image - Outputs to file

---

#### sd15-img2img.json (Image-to-Image)

**Type:** Image Transformation  
**Model:** v1-5-pruned-emaonly-fp16.safetensors

**Description:**  
Transform existing images with text prompts. Useful for style transfer, modifications, and artistic transformations.

**Usage:**
```bash
python3 generate.py \
    --workflow workflows/sd15-img2img.json \
    --input-image /path/to/source.png \
    --resize 512x512 \
    --crop cover \
    --denoise 0.7 \
    --prompt "watercolor painting style" \
    --output /tmp/artistic.png
```

**Parameters:**
- Input: Requires image file or URL (--input-image)
- Output: Matches input size (or --resize target)
- Denoise: 0.3-0.5 (subtle), 0.7-0.9 (creative)
- Steps: 20 (default)
- Generation time: 10-20 seconds

**Denoise Guide:**
- **0.3**: Very subtle changes, maintains most details
- **0.5**: Moderate changes, keeps structure
- **0.7**: Significant transformation, maintains composition
- **0.9**: Heavy transformation, mostly new image

**Key Nodes:**
1. Checkpoint Loader - SD 1.5 model
2. Load Image - Loads input from ComfyUI input folder
3. VAE Encode - Converts input to latent space
4. Positive/Negative Prompts - Transformation description
5. KSampler - Diffusion with denoise control
6. VAE Decode - Back to pixel space
7. Save Image - Output

---

#### wan22-t2v.json (Text-to-Video)

**Type:** Text-to-Video  
**Model:** wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors

**Description:**  
Generate videos from text prompts using Wan 2.2. Creates ~10 second videos with motion and camera movement.

**Usage:**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a drone shot flying over a coastal highway, waves crashing, cinematic" \
    --output /tmp/coastal.mp4
```

**Parameters:**
- Output: 848x480 MP4, 81 frames @ 8 fps (~10 seconds)
- Steps: 4 (with acceleration LoRA)
- CFG: 1.0
- Sampler: dpmpp_2m
- Generation time: 2-5 minutes

**Components:**
- Text Encoder: oldt5_xxl_fp8_e4m3fn_scaled.safetensors
- VAE: wan_2.1_vae.safetensors
- LoRA: wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors (acceleration)

**Prompt Tips:**
- Include camera movement (drone shot, pan, tilt, zoom)
- Specify action and motion explicitly
- Describe lighting and atmosphere
- Examples:
  - "camera slowly pans across a mountain landscape"
  - "person walking through park, sunny day, steadicam"
  - "ocean waves crashing, slow motion, sunset lighting"

---

#### wan22-i2v.json (Image-to-Video)

**Type:** Image-to-Video  
**Model:** wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors

**Description:**  
Animate existing images with motion. Adds camera movement or action to static photos.

**Usage:**
```bash
python3 generate.py \
    --workflow workflows/wan22-i2v.json \
    --input-image /path/to/photo.png \
    --prompt "camera slowly zooms in, subtle movement" \
    --output /tmp/animated.mp4
```

**Parameters:**
- Input: Requires image (--input-image)
- Output: 848x480 MP4, 81 frames @ 8 fps (~10 seconds)
- Steps: 4 (with acceleration LoRA)
- CFG: 1.0
- Generation time: 2-5 minutes

**Components:**
- Text Encoder: oldt5_xxl_fp8_e4m3fn_scaled.safetensors
- VAE: wan_2.1_vae.safetensors
- LoRA: wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors (acceleration)

**Prompt Tips:**
- Describe desired motion (pan, zoom, tilt)
- Specify camera movement type
- Focus on what action to add to the static image
- Examples:
  - "camera slowly pans right"
  - "gentle zoom in on subject"
  - "add subtle breathing motion"
  - "wind blowing through trees"

**Preprocessing:**
- Input image should be close to 848x480
- Use `--resize 848x480 --crop cover` for automatic preprocessing

---

### Creating Custom Workflows

#### Exporting from ComfyUI

1. Design workflow in ComfyUI GUI at http://192.168.1.215:8188
2. Click "Save" → "Export Workflow (JSON)"
3. Save to `workflows/` directory with descriptive name
4. Test with generate.py

#### Adding Metadata

Add a `_workflow_metadata` object to your exported JSON:

```json
{
  "_workflow_metadata": {
    "workflow_name": "Custom Workflow Name",
    "description": "What this workflow does",
    "model": "model_filename.safetensors",
    "output_resolution": "WIDTHxHEIGHT",
    "use_case": "When to use this workflow",
    "estimated_time": "Expected generation time"
  },
  "1": {
    "class_type": "CheckpointLoaderSimple",
    ...
  }
}
```

#### Validation

Always validate new workflows before committing:

```bash
# Dry-run validation
python3 generate.py --workflow workflows/custom.json --dry-run

# Test generation
python3 generate.py \
    --workflow workflows/custom.json \
    --prompt "test prompt" \
    --output /tmp/test.png
```

#### Best Practices

1. **Use descriptive filenames**: `sd15-portrait-style.json` not `workflow1.json`
2. **Include metadata**: Help others understand workflow purpose
3. **Test thoroughly**: Validate models exist, test with various prompts
4. **Document requirements**: Note any special LoRAs or input requirements
5. **Update docs**: Add entry to this file and README.md
6. **Version control**: Commit workflows with descriptive messages

---

## Generation Presets

Presets provide pre-configured parameter combinations for common use cases, making it easy to generate images with consistent quality settings.

### Using Presets

Basic usage:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "your prompt here" \
    --preset high-quality \
    --output output.png
```

Override specific parameters:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "your prompt" \
    --preset balanced \
    --seed 42 \
    --width 768 \
    --output output.png
```

### Available Presets

#### draft

**Purpose:** Quick previews and prompt testing  
**Speed:** Very fast (~5-10 seconds)  
**Quality:** Lower, may have artifacts

```yaml
steps: 10
cfg: 5.0
sampler: euler
scheduler: normal
```

**Use when:**
- Testing different prompts
- Iterating on composition
- Creating quick previews
- Speed is priority over quality

---

#### balanced

**Purpose:** Default quality/speed tradeoff  
**Speed:** Moderate (~15-30 seconds)  
**Quality:** Good for most purposes

```yaml
steps: 20
cfg: 7.0
sampler: euler_ancestral
scheduler: normal
```

**Use when:**
- General purpose generation
- Good balance needed
- Standard workflow outputs
- Default choice for most tasks

---

#### high-quality

**Purpose:** Final outputs and detailed work  
**Speed:** Slow (~45-90 seconds)  
**Quality:** High detail, minimal artifacts

```yaml
steps: 50
cfg: 7.5
sampler: dpmpp_2m_sde
scheduler: karras
```

**Use when:**
- Creating final deliverables
- Maximum detail needed
- Print or high-res output
- Quality is priority over speed

---

#### fast

**Purpose:** Quick generation with decent quality  
**Speed:** Fast (~10-20 seconds)  
**Quality:** Good compromise

```yaml
steps: 15
cfg: 7.0
sampler: dpmpp_2m
scheduler: normal
```

**Use when:**
- Need quick results
- Better than draft quality
- Iterating with feedback
- Batch processing

---

#### ultra

**Purpose:** Maximum quality, research use  
**Speed:** Very slow (2-5 minutes)  
**Quality:** Highest possible detail

```yaml
steps: 100
cfg: 8.0
sampler: dpmpp_2m_sde
scheduler: karras
```

**Use when:**
- Absolute maximum quality required
- Research or analysis
- Reference images
- Time is not a constraint
- **Note:** Diminishing returns beyond 50 steps

### Creating Custom Presets

Edit `presets.yaml` to add your own presets:

```yaml
presets:
  my-custom-preset:
    steps: 30
    cfg: 6.5
    sampler: dpmpp_2m
    scheduler: karras
    width: 768      # Optional
    height: 512     # Optional
```

Then use it:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "test" \
    --preset my-custom-preset
```

### Preset Selection Guide

| Use Case | Recommended Preset | Notes |
|----------|-------------------|-------|
| Testing prompts | `draft` | Fastest feedback |
| General work | `balanced` | Best all-around |
| Final outputs | `high-quality` | Publication ready |
| Batch processing | `fast` | Good speed/quality |
| Research | `ultra` | Maximum detail |

---

## Dynamic LoRA Injection

LoRAs (Low-Rank Adaptation) are small model adaptations that can modify generation behavior. Dynamic injection allows adding LoRAs at generation time without modifying workflow JSON files.

### CLI Arguments

#### `--lora NAME:STRENGTH`

Add a LoRA with specified strength. Can be repeated for multiple LoRAs.

**Format:** `--lora "filename.safetensors:strength"`

**Example:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a beautiful landscape" \
    --lora "style_lora.safetensors:0.8"
```

#### `--lora-preset PRESET_NAME`

Use a predefined LoRA preset from `lora_catalog.yaml`.

**Example:**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "person walking" \
    --lora-preset "text_to_video"
```

#### `--list-loras`

List all available LoRAs and presets, then exit.

### Usage Examples

**Single LoRA:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "cyberpunk cityscape, neon lights, rain" \
    --lora "cyberpunk_style.safetensors:0.7" \
    --output cyberpunk.png
```

**Multiple LoRAs (Chaining):**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "dancer performing, dynamic movement" \
    --lora "BoobPhysics_WAN_v6.safetensors:0.7" \
    --lora "BounceHighWan2_2.safetensors:0.6" \
    --output dancer.mp4
```

**Chain Order:**
```
Model → LoRA 1 → LoRA 2 → ... → Sampler
```

**LoRA Presets:**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "action scene with physics" \
    --lora-preset "text_to_video" \
    --output action.mp4
```

### LoRA Strength Guidelines

| Strength | Effect | Use Case |
|----------|--------|----------|
| 0.3-0.5 | Subtle | Minor style adjustments |
| 0.6-0.8 | Moderate | Typical style/physics LoRAs |
| 0.9-1.0 | Strong | Acceleration LoRAs, major changes |
| 1.0+ | Maximum | Some LoRAs work best at 1.0 or higher |

**Note:** Acceleration LoRAs (like 4-step LoRAs) typically require strength of exactly 1.0.

### How It Works

1. **Workflow Loading:** Load base workflow JSON
2. **LoRA Injection:** Insert LoraLoader nodes dynamically
3. **Connection Rewiring:** Update connections to chain through LoRAs
4. **Generation:** Send modified workflow to ComfyUI

**Before:**
```
CheckpointLoader → KSampler
```

**After (single LoRA):**
```
CheckpointLoader → LoraLoader → KSampler
```

**After (multiple LoRAs):**
```
CheckpointLoader → LoraLoader1 → LoraLoader2 → KSampler
```

### Compatibility

- ✅ SD 1.5 workflows (CheckpointLoaderSimple)
- ✅ Wan 2.2 workflows (UNETLoader + DualCLIPLoader)
- ✅ SDXL workflows (CheckpointLoaderSimple)
- ✅ Workflows with existing LoRAs (chains automatically)

---

## Metadata Tracking

ComfyGen automatically creates JSON metadata sidecars for every generated image, enabling experiment tracking, reproducibility, and parameter querying.

### Overview

When you generate an image, both the image **and** a JSON metadata file are uploaded to MinIO:

```
20260104_011032_output.png       # The generated image
20260104_011032_output.png.json  # The metadata sidecar
```

This metadata contains all parameters used to create the image.

### Metadata Format

The JSON sidecar includes:

```json
{
  "timestamp": "2026-01-04T01:10:32.123456",
  "prompt": "a beautiful sunset over mountains",
  "negative_prompt": "bad quality, blurry, low resolution",
  "workflow": "flux-dev.json",
  "seed": 12345,
  "steps": 30,
  "cfg": 7.5,
  "sampler": "euler",
  "scheduler": "normal",
  "loras": [
    {
      "name": "style-enhance.safetensors",
      "strength": 0.8
    }
  ],
  "preset": "high-quality",
  "validation_score": 0.85,
  "minio_url": "http://192.168.1.215:9000/comfy-gen/20260104_011032_output.png"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp of generation |
| `prompt` | string | Positive text prompt |
| `negative_prompt` | string | Negative prompt (empty string if none) |
| `workflow` | string | Workflow filename (e.g., "flux-dev.json") |
| `seed` | integer | Random seed used (actual value, not -1) |
| `steps` | integer | Number of sampling steps |
| `cfg` | float | CFG scale value |
| `sampler` | string | Sampler algorithm name |
| `scheduler` | string | Scheduler name |
| `loras` | array | List of LoRA objects with `name` and `strength` |
| `preset` | string | Preset name if used (null otherwise) |
| `validation_score` | float | CLIP validation score if validation was run |
| `minio_url` | string | Direct URL to the generated image |

### Usage

**Basic generation (metadata enabled by default):**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a serene lake at dawn" \
    --output output.png
```

Output:
```
[OK] Image available at: http://192.168.1.215:9000/comfy-gen/20260104_011032_output.png
[OK] Metadata available at: http://192.168.1.215:9000/comfy-gen/20260104_011032_output.png.json
```

**Disabling metadata:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "test image" \
    --no-metadata \
    --output test.png
```

### Reproducing a Generation

1. **Download the metadata:**
   ```bash
   curl http://192.168.1.215:9000/comfy-gen/20260104_011032_output.png.json > metadata.json
   ```

2. **Extract and re-run:**
   ```bash
   python3 generate.py \
       --workflow workflows/$(jq -r .workflow metadata.json) \
       --prompt "$(jq -r .prompt metadata.json)" \
       --negative-prompt "$(jq -r .negative_prompt metadata.json)" \
       --seed $(jq -r .seed metadata.json) \
       --steps $(jq -r .steps metadata.json) \
       --cfg $(jq -r .cfg metadata.json) \
       --output reproduced.png
   ```

### Querying Past Generations

**Find all generations with a specific prompt:**
```bash
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
    curl -s http://192.168.1.215:9000/comfy-gen/$file | \
        jq -r "select(.prompt | contains(\"sunset\")) | .minio_url"
done
```

**Find validated generations above threshold:**
```bash
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
    curl -s http://192.168.1.215:9000/comfy-gen/$file | \
        jq -r "select(.validation_score != null and .validation_score >= 0.8) | .minio_url"
done
```

### Technical Details

**Storage:**
- Metadata files are uploaded to the same MinIO bucket as images (`comfy-gen`)
- File naming: `<image_filename>.json`
- Content type: `application/json`
- Public read access (via bucket policy)

**Implementation:**

Metadata creation happens in `generate.py`:
1. **Extract workflow parameters** - `extract_workflow_params()` reads KSampler settings
2. **Extract LoRAs** - `extract_loras_from_workflow()` finds all LoRA nodes
3. **Create metadata** - `create_metadata_json()` assembles the complete JSON
4. **Upload** - `upload_metadata_to_minio()` saves to MinIO after image upload

---

## MinIO Object Storage

MinIO provides S3-compatible object storage for generated images and videos on moira. All generated assets are automatically uploaded and made publicly accessible via HTTP URLs.

### Installation

**Location on moira:**
- **Binary:** `C:\mlflow-artifacts\minio.exe`
- **Data directory:** `C:\mlflow-artifacts\data`

### Startup

**Starting MinIO manually:**

```powershell
# SSH to moira
ssh moira

# Start MinIO server
cd C:\mlflow-artifacts
.\minio.exe server .\data --console-address ":9001"
```

**MinIO should start automatically on moira boot.** If it doesn't respond after reboot, use the command above.

### Endpoints

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| MinIO API | 9000 | http://192.168.1.215:9000 | S3-compatible API for uploads/downloads |
| MinIO Console | 9001 | http://192.168.1.215:9001 | Web UI for bucket management |

### Health Check

Verify MinIO is running:

```bash
# Check API health
curl http://192.168.1.215:9000/minio/health/live

# Expected output: HTTP 200 OK (no body)
```

### Credentials

**Default credentials (local development only):**
- **Username:** `minioadmin`
- **Password:** `minioadmin`

**⚠️ WARNING:** These are the default MinIO credentials and should ONLY be used for local development. For production deployments, these credentials MUST be changed immediately using the `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` environment variables.

These credentials are used by:
- MinIO Console login (http://192.168.1.215:9001)
- `generate.py` for automated uploads (configured in code)
- Manual S3 client access

**Security note:** These are development credentials. MinIO is only accessible on the local network (192.168.1.0/24).

### Bucket Configuration

**Primary bucket:** `comfy-gen`

This bucket stores all generated images, videos, and metadata JSON files.

**Public access:** The `comfy-gen` bucket is configured with public read access, allowing generated images to be viewed directly via URL without authentication.

**Setting bucket policy (if needed):**

```bash
# Make bucket publicly readable
python3 scripts/set_bucket_policy.py
```

**Creating the bucket (first-time setup):**

```bash
# Create comfy-gen bucket
python3 scripts/create_bucket.py
```

### Accessing Images

**Direct URL format:**
```
http://192.168.1.215:9000/comfy-gen/<filename>
```

**Example:**
```
http://192.168.1.215:9000/comfy-gen/20260104_011032_output.png
```

**Listing bucket contents:**

```bash
# List all files in comfy-gen bucket
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+'
```

### SSH Tunnel (Secure Remote Access)

For accessing MinIO from machines without direct network access:

```bash
# Create SSH tunnel
python3 scripts/minio_tunnel.py

# Then access via localhost
open http://localhost:9000/comfy-gen/
```

The tunnel script creates an SSH port forward: `localhost:9000` → `moira:9000`

### Troubleshooting

**MinIO not responding:**

1. Check if process is running:
   ```powershell
   ssh moira "tasklist | findstr minio"
   ```

2. Restart MinIO:
   ```powershell
   ssh moira "cd C:\mlflow-artifacts && .\minio.exe server .\data --console-address ':9001'"
   ```

**Access denied errors:**

Bucket policy may need to be reset:
```bash
python3 scripts/set_bucket_policy.py
```

**Images not uploading:**

1. Verify MinIO health: `curl http://192.168.1.215:9000/minio/health/live`
2. Check bucket exists: `curl -s http://192.168.1.215:9000/comfy-gen/`
3. Verify credentials in `generate.py` (minioadmin/minioadmin)

---

## See Also

- [USAGE.md](USAGE.md) - Complete usage guide for CLI and MCP
- [MODEL_REGISTRY.md](MODEL_REGISTRY.md) - Available models and LoRAs
- [API_REFERENCE.md](API_REFERENCE.md) - Internal module documentation

---

**Documentation Policy:** This is an authoritative reference document. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only.
