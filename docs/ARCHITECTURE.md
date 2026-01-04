# ComfyGen Architecture

This document describes the system architecture, workflows, presets, LoRA injection, and metadata tracking.

## Table of Contents

- [System Overview](#system-overview)
- [Workflows](#workflows)
- [Generation Presets](#generation-presets)
- [Dynamic LoRA Injection](#dynamic-lora-injection)
- [Metadata Tracking](#metadata-tracking)

---

## System Overview

### Infrastructure

| Machine | Role | IP |
|---------|------|-----|
| magneto | Development workstation | 192.168.1.124 |
| moira | ComfyUI server + MinIO + GPU (RTX 5090) | 192.168.1.215 |
| ant-man | GitHub Actions runner (ARM64) | 192.168.1.253 |

### Data Flow

```
magneto (git push) --> GitHub --> ant-man (runner) --> moira (ComfyUI)
                                                          |
                                                          v
                                                     MinIO storage
                                                          |
                                                          v
                                              http://192.168.1.215:9000/comfy-gen/
```

### Components

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

---

## Workflows

A workflow is a JSON file that defines the complete generation pipeline.

### Workflow Metadata

Each workflow JSON file includes a `_workflow_metadata` object at the root level:

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

### Available Workflows

#### flux-dev.json

**Type:** Text-to-Image  
**Model:** v1-5-pruned-emaonly-fp16.safetensors  
**Output:** 512x512 PNG  
**Time:** 10-15 seconds

Simple text-to-image generation using Stable Diffusion 1.5. Fast and reliable for general-purpose image generation.

**Usage:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a mountain landscape at sunset" \
    --negative-prompt "blurry, low quality" \
    --output /tmp/landscape.png
```

**Key Nodes:**
1. Checkpoint Loader - Loads SD 1.5 model
2. Positive Prompt - Text description
3. Negative Prompt - What to avoid
4. Empty Latent - Creates 512x512 blank latent
5. KSampler - Diffusion sampling
6. VAE Decode - Converts latent to pixels
7. Save Image - Outputs to file

#### sd15-img2img.json

**Type:** Image Transformation  
**Model:** v1-5-pruned-emaonly-fp16.safetensors  
**Output:** Variable PNG  
**Time:** 10-20 seconds

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
    --negative-prompt "photograph, realistic" \
    --output /tmp/artistic.png
```

**Denoise Guide:**
- **0.3**: Very subtle changes, maintains most details
- **0.5**: Moderate changes, keeps structure
- **0.7**: Significant transformation, maintains composition
- **0.9**: Heavy transformation, mostly new image

#### wan22-t2v.json

**Type:** Text-to-Video  
**Model:** wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors  
**Output:** 848x480 MP4, 81 frames @ 8 fps (~10 seconds)  
**Time:** 2-5 minutes

Generate videos from text prompts using Wan 2.2.

**Usage:**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a drone shot flying over a coastal highway, waves crashing, cinematic" \
    --output /tmp/coastal.mp4
```

**Components:**
- Text Encoder: oldt5_xxl_fp8_e4m3fn_scaled.safetensors
- VAE: wan_2.1_vae.safetensors
- LoRA: wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors (acceleration)

**Prompt Tips:**
- Include camera movement (drone shot, pan, tilt, zoom)
- Specify action and motion explicitly
- Describe lighting and atmosphere
- Keep prompts focused on motion/action

#### wan22-i2v.json

**Type:** Image-to-Video  
**Model:** wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors  
**Output:** 848x480 MP4, 81 frames @ 8 fps (~10 seconds)  
**Time:** 2-5 minutes

Animate existing images with motion.

**Usage:**
```bash
python3 generate.py \
    --workflow workflows/wan22-i2v.json \
    --input-image /path/to/photo.png \
    --prompt "camera slowly zooms in, subtle movement" \
    --output /tmp/animated.mp4
```

**Prompt Tips:**
- Describe desired motion (pan, zoom, tilt)
- Specify camera movement type
- Focus on what action to add to the static image
- Keep prompts concise and motion-focused

### Workflow Comparison

| Workflow | Type | Input Image | Output | Generation Time | Best For |
|----------|------|-------------|--------|-----------------|----------|
| flux-dev.json | T2I | No | 512x512 PNG | 10-15s | Quick image generation |
| sd15-img2img.json | I2I | Yes | Variable PNG | 10-20s | Image transformation |
| wan22-t2v.json | T2V | No | 848x480 MP4 | 2-5min | Video from text |
| wan22-i2v.json | I2V | Yes | 848x480 MP4 | 2-5min | Animate images |

### Creating Custom Workflows

1. **Design in ComfyUI GUI** at http://192.168.1.215:8188
2. **Export:** Click "Save" → "Export Workflow (JSON)"
3. **Add Metadata:** Include `_workflow_metadata` object
4. **Save:** Store in `workflows/` directory
5. **Test:** Validate with `--dry-run` and test generation

**Example with metadata:**
```json
{
  "_workflow_metadata": {
    "workflow_name": "SD 1.5 Portrait Generation",
    "description": "Optimized for generating portrait photos with high detail",
    "model": "v1-5-pruned-emaonly-fp16.safetensors",
    "output_resolution": "512x768",
    "use_case": "Portrait photography, headshots, character portraits",
    "estimated_time": "15-20 seconds on RTX 5090"
  },
  "1": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
    }
  }
}
```

---

## Generation Presets

Presets provide pre-configured parameter combinations for common use cases.

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

### Using Presets

```bash
# Basic usage
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "detailed fantasy scene" \
    --preset high-quality \
    --output /tmp/scene.png

# Override specific parameters
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "robot in factory" \
    --preset balanced \
    --seed 42 \
    --width 768 \
    --output /tmp/robot.png
```

### Preset Selection Guide

| Use Case | Recommended Preset | Notes |
|----------|-------------------|-------|
| Testing prompts | `draft` | Fastest feedback |
| General work | `balanced` | Best all-around |
| Final outputs | `high-quality` | Publication ready |
| Batch processing | `fast` | Good speed/quality |
| Research | `ultra` | Maximum detail |

### Creating Custom Presets

Edit `presets.yaml`:

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

---

## Dynamic LoRA Injection

LoRAs (Low-Rank Adaptation) are small model adaptations that modify generation behavior. ComfyGen supports dynamic injection via CLI arguments.

### CLI Arguments

**Single LoRA:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "cyberpunk cityscape, neon lights, rain" \
    --lora "cyberpunk_style.safetensors:0.7" \
    --output cyberpunk.png
```

**Multiple LoRAs (chaining):**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "dancer performing, dynamic movement" \
    --lora "BoobPhysics_WAN_v6.safetensors:0.7" \
    --lora "BounceHighWan2_2.safetensors:0.6" \
    --output dancer.mp4
```

**LoRA Presets:**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "action scene with physics" \
    --lora-preset "text_to_video" \
    --output action.mp4
```

**List Available LoRAs:**
```bash
python3 generate.py --list-loras
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

### Node Structure

Generated LoRA nodes:

```json
{
  "class_type": "LoraLoader",
  "inputs": {
    "model": ["1", 0],
    "clip": ["1", 1],
    "lora_name": "lora_file.safetensors",
    "strength_model": 0.8,
    "strength_clip": 0.8
  },
  "_meta": {
    "title": "LoRA: lora_file.safetensors"
  }
}
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

### Metadata Format

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
| `validation_score` | float | CLIP validation score if validation was run (null otherwise) |
| `minio_url` | string | Direct URL to the generated image |

### Usage

**Basic Generation (metadata enabled by default):**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a serene lake at dawn" \
    --output output.png
```

**With Validation:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "single red car on empty road" \
    --validate \
    --output car.png
```

**Disable Metadata:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "test image" \
    --no-metadata \
    --output test.png
```

### Reproducing a Generation

1. **Download metadata:**
   ```bash
   curl http://192.168.1.215:9000/comfy-gen/20260104_011032_output.png.json > metadata.json
   ```

2. **Extract parameters:**
   ```bash
   cat metadata.json | jq .
   ```

3. **Re-run with same parameters:**
   ```bash
   python3 generate.py \
       --workflow workflows/$(jq -r .workflow metadata.json) \
       --prompt "$(jq -r .prompt metadata.json)" \
       --seed $(jq -r .seed metadata.json) \
       --steps $(jq -r .steps metadata.json) \
       --cfg $(jq -r .cfg metadata.json) \
       --sampler $(jq -r .sampler metadata.json) \
       --scheduler $(jq -r .scheduler metadata.json) \
       --output reproduced.png
   ```

### Querying Past Generations

**Find generations with specific prompt:**
```bash
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
    curl -s http://192.168.1.215:9000/comfy-gen/$file | \
        jq -r "select(.prompt | contains(\"sunset\")) | .minio_url"
done
```

**Find generations by seed range:**
```bash
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
    curl -s http://192.168.1.215:9000/comfy-gen/$file | \
        jq -r "select(.seed >= 10000 and .seed <= 20000) | .minio_url"
done
```

**Find validated generations above threshold:**
```bash
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
    curl -s http://192.168.1.215:9000/comfy-gen/$file | \
        jq -r "select(.validation_score != null and .validation_score >= 0.8) | .minio_url"
done
```

### Implementation

Metadata creation happens in `generate.py`:

1. **Extract workflow parameters** - `extract_workflow_params()` reads KSampler settings
2. **Extract LoRAs** - `extract_loras_from_workflow()` finds all LoRA nodes
3. **Create metadata** - `create_metadata_json()` assembles the complete JSON
4. **Upload** - `upload_metadata_to_minio()` saves to MinIO after image upload

### Storage

- Metadata files are uploaded to the same MinIO bucket as images (`comfy-gen`)
- File naming: `<image_filename>.json` (e.g., `image.png` → `image.png.json`)
- Content type: `application/json`
- Public read access (via bucket policy)

---

## See Also

- [USAGE.md](USAGE.md) - Complete usage guide with examples
- [API_REFERENCE.md](API_REFERENCE.md) - Internal module and function documentation
- [MODEL_REGISTRY.md](MODEL_REGISTRY.md) - Complete model inventory
