# Workflow Documentation

This document describes the available ComfyUI workflows and their metadata structure.

## Table of Contents

- [Workflow Metadata](#workflow-metadata)
- [Available Workflows](#available-workflows)
- [Creating Custom Workflows](#creating-custom-workflows)

## Workflow Metadata

Each workflow JSON file now includes a `_workflow_metadata` object at the root level with the following fields:

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

## Available Workflows

### flux-dev.json

**Name:** SD 1.5 Basic Generation  
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
2. Positive Prompt - Text description of desired image
3. Negative Prompt - What to avoid
4. Empty Latent - Creates 512x512 blank latent
5. KSampler - Diffusion sampling
6. VAE Decode - Converts latent to pixels
7. Save Image - Outputs to file

---

### sd15-img2img.json

**Name:** SD 1.5 Image-to-Image  
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
    --negative-prompt "photograph, realistic" \
    --output /tmp/artistic.png
```

**Parameters:**
- Input: Requires image file or URL (--input-image)
- Output: Matches input size (or --resize target)
- Denoise: 0.3-0.5 (subtle), 0.7-0.9 (creative)
- Steps: 20 (default)
- Generation time: 10-20 seconds

**Preprocessing Options:**
- `--resize WxH`: Resize input image
- `--crop MODE`: Crop mode (center, cover, contain)
- `--denoise FLOAT`: Transformation strength

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

### wan22-t2v.json

**Name:** Wan 2.2 Text-to-Video  
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
- Keep prompts focused on motion/action
- Examples:
  - "camera slowly pans across a mountain landscape"
  - "person walking through park, sunny day, steadicam"
  - "ocean waves crashing, slow motion, sunset lighting"

**Key Nodes:**
- Text encoding nodes for T5
- Wan 2.2 diffusion model loader
- Acceleration LoRA (4-step)
- Video sampler
- Video VAE decoder
- Save video node

---

### wan22-i2v.json

**Name:** Wan 2.2 Image-to-Video  
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
- Keep prompts concise and motion-focused
- Examples:
  - "camera slowly pans right"
  - "gentle zoom in on subject"
  - "add subtle breathing motion"
  - "wind blowing through trees"

**Preprocessing:**
- Input image should be close to 848x480
- Use `--resize 848x480 --crop cover` for automatic preprocessing

**Key Nodes:**
- Load input image
- Text encoding for motion prompt
- Wan 2.2 I2V model loader
- Acceleration LoRA (4-step)
- I2V sampler with image conditioning
- Video VAE decoder
- Save video

---

## Creating Custom Workflows

### Exporting from ComfyUI

1. Design workflow in ComfyUI GUI at http://192.168.1.215:8188
2. Click "Save" → "Export Workflow (JSON)"
3. Save to `workflows/` directory with descriptive name
4. Test with generate.py

### Adding Metadata

Add a `_workflow_metadata` object to your exported JSON:

```json
{
  "_workflow_metadata": {
    "workflow_name": "Custom Workflow Name",
    "description": "What this workflow does",
    "model": "model_filename.safetensors",
    "output_resolution": "WIDTHxHEIGHT",
    "use_case": "When to use this workflow",
    "estimated_time": "Expected generation time",
    "nodes": {
      "1": "Node 1 description",
      "2": "Node 2 description"
    }
  },
  "1": {
    "class_type": "CheckpointLoaderSimple",
    ...
  }
}
```

### Validation

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

### Best Practices

1. **Use descriptive filenames**: `sd15-portrait-style.json` not `workflow1.json`
2. **Include metadata**: Help others understand workflow purpose
3. **Test thoroughly**: Validate models exist, test with various prompts
4. **Document requirements**: Note any special LoRAs or input requirements
5. **Update docs**: Add entry to this file and README.md
6. **Version control**: Commit workflows with descriptive messages

### Example Custom Workflow

```json
{
  "_workflow_metadata": {
    "workflow_name": "SD 1.5 Portrait Generation",
    "description": "Optimized for generating portrait photos with high detail",
    "model": "v1-5-pruned-emaonly-fp16.safetensors",
    "output_resolution": "512x768",
    "default_steps": 40,
    "use_case": "Portrait photography, headshots, character portraits",
    "estimated_time": "15-20 seconds on RTX 5090",
    "recommended_prompts": [
      "portrait photo of a person, professional lighting",
      "headshot, studio lighting, soft focus background"
    ],
    "recommended_negative": "blurry, low quality, distorted face, multiple heads",
    "nodes": {
      "1": "Checkpoint Loader",
      "2": "Portrait-optimized positive prompt",
      "3": "Face-focused negative prompt",
      "4": "Empty Latent - 512x768 for portrait aspect ratio",
      "5": "KSampler - 40 steps for detail",
      "6": "VAE Decode",
      "7": "Save Image"
    }
  },
  "1": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
    }
  },
  ...
}
```

## Workflow Comparison

| Workflow | Type | Input Image | Output | Generation Time | Best For |
|----------|------|-------------|--------|-----------------|----------|
| flux-dev.json | T2I | No | 512x512 PNG | 10-15s | Quick image generation |
| sd15-img2img.json | I2I | Yes | Variable PNG | 10-20s | Image transformation |
| wan22-t2v.json | T2V | No | 848x480 MP4 | 2-5min | Video from text |
| wan22-i2v.json | I2V | Yes | 848x480 MP4 | 2-5min | Animate images |

## See Also

- [AGENT_GUIDE.md](AGENT_GUIDE.md) - Decision tree for workflow selection
- [MODEL_REGISTRY.md](MODEL_REGISTRY.md) - Available models and compatibility
- [API_REFERENCE.md](API_REFERENCE.md) - Programmatic workflow usage
