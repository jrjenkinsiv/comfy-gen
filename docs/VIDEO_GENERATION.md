# Video Generation Guide

## Overview

ComfyGen supports programmatic video generation using **Wan 2.2** models. This guide covers:

- Text-to-Video (T2V) generation
- Image-to-Video (I2V) animation
- Video parameter control
- LoRA selection for video
- Best practices and troubleshooting

## Quick Start

### Text-to-Video

```bash
# Basic video generation
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "a woman walking through a park on a sunny day" \
  --output /tmp/walk.mp4

# Custom duration and resolution
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "ocean waves crashing on rocks" \
  --length 161 \
  --fps 16 \
  --video-resolution 1280x720 \
  --output /tmp/waves.mp4

# Using preset
python3 generate.py \
  --preset video-fast \
  --prompt "city traffic timelapse" \
  --output /tmp/traffic.mp4
```

### Image-to-Video

```bash
# Animate an existing image
python3 generate.py \
  --workflow workflows/wan22-i2v.json \
  --input-image /tmp/portrait.png \
  --prompt "subtle head movement, breathing, natural motion" \
  --output /tmp/animated.mp4

# With physics LoRAs
python3 generate.py \
  --workflow workflows/wan22-i2v.json \
  --input-image /tmp/portrait.png \
  --prompt "walking forward, natural body movement" \
  --lora "BoobPhysics_WAN_v6.safetensors:0.7" \
  --length 81 \
  --fps 16 \
  --output /tmp/walk_anim.mp4
```

## Video Parameters

### Frame Count / Duration

The `--length` (or `--frames`) parameter controls video duration:

**Duration Math:**
```
Duration (seconds) = Frames / FPS

Examples:
- 81 frames ÷ 16 fps = 5.06 seconds
- 161 frames ÷ 16 fps = 10.06 seconds
- 241 frames ÷ 16 fps = 15.06 seconds
```

**Common Frame Counts:**
| Frames | @ 16fps | @ 24fps | @ 30fps |
|--------|---------|---------|---------|
| 81     | ~5s     | ~3.4s   | ~2.7s   |
| 161    | ~10s    | ~6.7s   | ~5.4s   |
| 241    | ~15s    | ~10s    | ~8s     |

**CLI Usage:**
```bash
# Short clip (5 seconds)
--length 81 --fps 16

# Medium clip (10 seconds)
--length 161 --fps 16

# Long clip (15 seconds)
--length 241 --fps 16
```

### Frame Rate (FPS)

Controls playback speed. Higher FPS = smoother motion.

**Common FPS Values:**
- `8` fps - Choppy, retro look
- `16` fps - Standard (default for Wan 2.2)
- `24` fps - Cinematic
- `30` fps - Smooth, broadcast quality

```bash
# Cinematic 24fps
--fps 24

# Broadcast 30fps
--fps 30
```

### Resolution

Use `--video-resolution WxH` to set video dimensions:

**Common Resolutions:**
- `848x480` - SD (default)
- `1280x720` - HD 720p
- `1920x1080` - Full HD 1080p
- `640x360` - Low-res draft

**IMPORTANT:** Higher resolutions require more VRAM and take longer to generate.

```bash
# HD 720p video
--video-resolution 1280x720

# Full HD 1080p (requires significant VRAM)
--video-resolution 1920x1080
```

## Workflows

### High-Noise vs Low-Noise Models

ComfyGen includes two workflow variants for each type:

| Workflow | Model Type | Use Case |
|----------|------------|----------|
| `wan22-t2v.json` | High-noise | Default, general-purpose T2V |
| `wan22-t2v-low.json` | Low-noise | Smoother, less noisy T2V |
| `wan22-i2v.json` | High-noise | Default I2V animation |
| `wan22-i2v-low.json` | Low-noise | Smoother I2V animation |

**When to use low-noise:**
- Subtle motions (breathing, head movement)
- Clean, professional look
- Faces and portraits

**When to use high-noise:**
- Dynamic action scenes
- Creative/artistic effects
- Fast movement

```bash
# Use low-noise for subtle animation
python3 generate.py \
  --workflow workflows/wan22-i2v-low.json \
  --input-image portrait.png \
  --prompt "gentle breathing, eyes blinking"
```

## Video Presets

Pre-configured parameter sets for common scenarios:

### video-fast
Fast 4-step generation with acceleration LoRA (already in workflow).

```bash
python3 generate.py --preset video-fast --prompt "sunset timelapse"
```

**Parameters:**
- Steps: 4
- CFG: 1.0
- Length: 81 frames
- FPS: 16
- Validation: disabled

### video-quality
High-quality 30-step generation with physics LoRAs.

```bash
python3 generate.py --preset video-quality --prompt "woman dancing"
```

**Parameters:**
- Steps: 30
- CFG: 6.0
- Length: 81 frames
- FPS: 16
- LoRAs: BoobPhysics_WAN_v6.safetensors (0.7), BounceHighWan2_2.safetensors (0.7)

### video-nsfw
Adult content with body enhancement and physics.

```bash
python3 generate.py --preset video-nsfw --prompt "explicit motion prompt"
```

**Parameters:**
- Steps: 30
- CFG: 7.0
- Length: 81 frames
- FPS: 16
- LoRAs: BoobPhysics_WAN_v6.safetensors (0.8), wan-thiccum-v3.safetensors (0.7)

## LoRA Selection for Video

### CRITICAL: Video vs Image LoRAs

**Wan 2.2 video LoRAs are NOT compatible with SD 1.5 / Flux image generation!**

Always verify LoRA compatibility using `lora_catalog.yaml` or CivitAI API.

### LoRA Categories

#### Acceleration LoRAs
Reduce generation from 30 steps to 4 steps. **ALWAYS use strength 1.0**.

**T2V High-Noise:**
```bash
--lora "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors:1.0"
```

**T2V Low-Noise:**
```bash
--lora "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors:1.0"
```

**I2V High-Noise:**
```bash
--lora "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors:1.0"
```

**I2V Low-Noise:**
```bash
--lora "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors:1.0"
```

**IMPORTANT:** Acceleration LoRAs are already included in the default `wan22-t2v.json` and `wan22-i2v.json` workflows for 4-step generation. For 30-step quality generation, remove or override them.

#### Physics LoRAs
Add realistic body physics and motion. Use strength 0.6-0.8.

```bash
# Realistic body physics
--lora "BoobPhysics_WAN_v6.safetensors:0.7"

# Dynamic bounce (high-noise)
--lora "BounceHighWan2_2.safetensors:0.7"

# Dynamic bounce (low-noise)
--lora "BounceLowWan2_2.safetensors:0.7"
```

#### Body Enhancement LoRAs
Character-focused enhancements. Use strength 0.5-0.9.

```bash
--lora "wan-thiccum-v3.safetensors:0.7"
```

### Stacking LoRAs

You can combine multiple LoRAs for cumulative effects:

```bash
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "woman dancing energetically" \
  --lora "BoobPhysics_WAN_v6.safetensors:0.7" \
  --lora "BounceHighWan2_2.safetensors:0.6" \
  --steps 30
```

**Best Practices:**
- Physics LoRAs: 0.6-0.8
- Body enhancement: 0.5-0.9
- Acceleration LoRAs: Always 1.0
- Don't stack too many (2-3 max recommended)

## MCP Server Usage

The MCP server exposes video generation tools:

```python
# Text-to-video
await generate_video(
    prompt="a sunset over mountains",
    width=848,
    height=480,
    frames=81,
    fps=16,
    steps=30,
    cfg=6.0,
    seed=-1
)

# Image-to-video
await image_to_video(
    input_image="/path/to/image.png",
    prompt="gentle movement, breathing",
    frames=81,
    fps=16,
    steps=30,
    seed=-1
)
```

## Troubleshooting

### Video not generating
- **Check model availability:** Ensure Wan 2.2 models are installed
- **Check VRAM:** High-resolution videos require significant memory
- **Check workflow:** Verify `EmptyLatentVideo` and `VHS_VideoCombine` nodes exist

### Video is too short/long
- Adjust `--length` parameter
- Calculate: `seconds = frames / fps`
- Example: 10 seconds at 16fps = 160 frames

### Low quality / noisy output
- Try low-noise workflows (`wan22-t2v-low.json`)
- Increase steps (30 instead of 4)
- Reduce CFG if too rigid
- Add physics LoRAs for natural motion

### LoRA not working
- Verify LoRA is compatible with Wan 2.2 (check `lora_catalog.yaml`)
- Check LoRA strength (acceleration = 1.0, physics = 0.6-0.8)
- Ensure LoRA matches model variant (high_noise vs low_noise)

### Out of memory
- Reduce resolution (`--video-resolution 640x360`)
- Reduce frame count (`--length 41`)
- Use 4-step acceleration workflow

## Best Practices

### Prompt Engineering for Video

Video prompts should describe **motion** and **change**, not static scenes:

**Good video prompts:**
- "a woman walking forward through a park"
- "ocean waves rolling onto the beach"
- "camera panning across a city skyline"
- "dancer spinning gracefully"

**Bad video prompts (too static):**
- "a beautiful woman standing still"
- "a car parked in a driveway"
- "portrait of a person"

**I2V Motion Prompts:**
For image-to-video, describe the **desired motion**:
- "head turning left, eyes blinking"
- "walking forward naturally"
- "breathing, chest rising and falling"
- "wind blowing hair gently"

### Quality Settings

**Draft (fast preview):**
- Use `video-fast` preset
- 4 steps, low resolution
- Validation disabled

**Production (final output):**
- Use `video-quality` preset
- 30 steps, full resolution
- Physics LoRAs
- Validation enabled

**NSFW Content:**
- Use `video-nsfw` preset
- Explicit prompts
- Physics + body LoRAs
- Higher CFG (7.0+)

### Performance Optimization

**Reduce generation time:**
1. Use 4-step acceleration LoRAs (included in default workflows)
2. Lower resolution (`640x360` or `848x480`)
3. Shorter clips (81 frames or less)
4. Disable validation (`--no-validate`)

**Improve quality:**
1. Use 30 steps without acceleration LoRAs
2. Add physics LoRAs
3. Use low-noise workflows
4. Higher resolution (720p or 1080p)
5. Enable validation

## Examples

### Example 1: Quick Test
```bash
python3 generate.py \
  --preset video-fast \
  --prompt "sunset over ocean" \
  --output /tmp/sunset.mp4
```

### Example 2: High-Quality Scene
```bash
python3 generate.py \
  --workflow workflows/wan22-t2v.json \
  --prompt "elegant woman walking through garden, flowing dress, golden hour lighting" \
  --steps 30 \
  --cfg 6.0 \
  --length 161 \
  --fps 16 \
  --video-resolution 1280x720 \
  --lora "BoobPhysics_WAN_v6.safetensors:0.7" \
  --lora "BounceHighWan2_2.safetensors:0.6" \
  --output /tmp/garden_walk.mp4
```

### Example 3: Portrait Animation
```bash
python3 generate.py \
  --workflow workflows/wan22-i2v-low.json \
  --input-image /tmp/portrait.png \
  --prompt "subtle head movement, eyes blinking naturally, gentle breathing" \
  --steps 30 \
  --length 81 \
  --fps 24 \
  --output /tmp/portrait_anim.mp4
```

### Example 4: NSFW Content
```bash
python3 generate.py \
  --preset video-nsfw \
  --prompt "[explicit prompt]" \
  --length 161 \
  --output /tmp/explicit.mp4
```

## Advanced Topics

### Frame Interpolation
For smoother playback, you can interpolate frames using external tools:
- FFmpeg frame interpolation
- RIFE (video frame interpolation)
- Butterflow

### Video Extension
Currently not supported - requires custom workflow. Track issue for updates.

### Custom Workflows
You can create custom Wan 2.2 workflows by:
1. Copying an existing workflow (`wan22-t2v.json`)
2. Modifying node parameters in ComfyUI GUI
3. Exporting as JSON
4. Using with `--workflow` flag

## See Also

- `docs/USAGE.md` - General usage guide
- `docs/LORA_GUIDE.md` - Complete LoRA selection guide
- `lora_catalog.yaml` - Full LoRA inventory with compatibility info
- `presets.yaml` - All generation presets
