# Generation Presets

This document describes the generation presets system for ComfyGen.

## Overview

Presets provide pre-configured parameter combinations for common use cases, making it easy to generate images with consistent quality settings without remembering all the parameters.

## Using Presets

### Basic Usage

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "your prompt here" \
    --preset high-quality \
    --output output.png
```

### Overriding Preset Values

Individual parameters can override preset values:

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "your prompt" \
    --preset balanced \
    --seed 42 \
    --width 768 \
    --output output.png
```

In this example, the `balanced` preset is used, but the seed and width are overridden with custom values.

## Available Presets

### draft
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

### balanced
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

### high-quality
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

### fast
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

### ultra
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
- **Note:** Diminishing returns beyond 50 steps for most images

## Parameter Explanations

### Steps
Number of sampling iterations. More steps generally produce better quality but with diminishing returns.

- **10 steps:** Draft quality
- **20 steps:** Standard quality
- **50 steps:** High quality
- **100+ steps:** Minimal improvement over 50

### CFG (Classifier-Free Guidance)
Controls how strictly the model follows the prompt.

- **5.0:** Loose interpretation, more creative
- **7.0:** Balanced adherence (recommended)
- **8.0:** Strict prompt following
- **Higher:** Risk of over-saturation

### Sampler
Algorithm used for generating the image.

- **euler:** Simple, fast, good for drafts
- **euler_ancestral:** Adds variation, good for exploration
- **dpmpp_2m:** Fast with good quality
- **dpmpp_2m_sde:** Slower but higher quality

### Scheduler
Noise schedule used during generation.

- **normal:** Standard linear schedule
- **karras:** Better detail preservation
- **exponential:** Alternative distribution

## Creating Custom Presets

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

## Preset Selection Guide

| Use Case | Recommended Preset | Notes |
|----------|-------------------|-------|
| Testing prompts | `draft` | Fastest feedback |
| General work | `balanced` | Best all-around |
| Final outputs | `high-quality` | Publication ready |
| Batch processing | `fast` | Good speed/quality |
| Research | `ultra` | Maximum detail |
| Custom dimensions | `balanced` + `--width/--height` | Override dimensions |
| Reproducible | Any + `--seed` | Add seed for consistency |

## Best Practices

1. **Start with presets:** Use `balanced` as your baseline
2. **Iterate efficiently:** Use `draft` for prompt testing, then switch to `high-quality`
3. **Document your choices:** Record which preset works best for different types of images
4. **Override sparingly:** Only override specific parameters when needed
5. **Test seeds:** Find a good seed with `draft`, then use same seed with `high-quality`

## Examples

### Example 1: Fast Iteration Workflow
```bash
# Test prompt with draft
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "cyberpunk street" --preset draft --output test1.png

# Found good composition, now generate high quality
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "cyberpunk street" --preset high-quality --seed 12345 --output final.png
```

### Example 2: Custom Dimensions with Preset
```bash
# Use high-quality preset but with custom aspect ratio
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "wide landscape" --preset high-quality \
    --width 768 --height 512 --output landscape.png
```

### Example 3: Reproducible Batch Generation
```bash
# Generate multiple images with same quality settings
for i in {1..5}; do
    python3 generate.py --workflow workflows/flux-dev.json \
        --prompt "variation $i" --preset balanced \
        --seed $i --output "batch_$i.png"
done
```

## See Also

- [AGENT_GUIDE.md](AGENT_GUIDE.md) - Complete parameter reference
- [examples/advanced_params.py](../examples/advanced_params.py) - Example usage
- [presets.yaml](../presets.yaml) - Preset definitions
