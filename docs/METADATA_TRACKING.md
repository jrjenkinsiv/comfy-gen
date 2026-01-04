# Experiment Tracking with JSON Metadata

ComfyGen automatically creates JSON metadata sidecars for every generated image, enabling experiment tracking, reproducibility, and parameter querying.

## Overview

When you generate an image, ComfyGen uploads both the image **and** a JSON metadata file to MinIO:

```
20260104_011032_output.png       # The generated image
20260104_011032_output.png.json  # The metadata sidecar
```

This metadata contains all parameters used to create the image, making it easy to:
- **Reproduce** exact generations
- **Debug** why an image failed validation
- **Query** past generations by seed, prompt, or parameters
- **Compare** experiments and iterate on prompts

## Metadata Format

The JSON sidecar includes the following fields:

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

## Usage Examples

### Basic Generation (metadata enabled by default)

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

### With Validation

When validation is enabled, the `validation_score` field is populated:

```bash
python3 generate.py \
  --workflow workflows/flux-dev.json \
  --prompt "single red car on empty road" \
  --validate \
  --output car.png
```

The metadata will include:
```json
{
  "validation_score": 0.87,
  ...
}
```

### Disabling Metadata

Use `--no-metadata` to skip JSON sidecar creation:

```bash
python3 generate.py \
  --workflow workflows/flux-dev.json \
  --prompt "test image" \
  --no-metadata \
  --output test.png
```

## Reproducing a Generation

To reproduce an exact generation from metadata:

1. **Download the metadata:**
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
     --negative-prompt "$(jq -r .negative_prompt metadata.json)" \
     --seed $(jq -r .seed metadata.json) \
     --steps $(jq -r .steps metadata.json) \
     --cfg $(jq -r .cfg metadata.json) \
     --sampler $(jq -r .sampler metadata.json) \
     --scheduler $(jq -r .scheduler metadata.json) \
     --output reproduced.png
   ```

## Querying Past Generations

You can query metadata files to find specific generations:

### Find all generations with a specific prompt

```bash
# List all metadata files
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'

# Download and search
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
  curl -s http://192.168.1.215:9000/comfy-gen/$file | \
    jq -r "select(.prompt | contains(\"sunset\")) | .minio_url"
done
```

### Find generations by seed range

```bash
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
  curl -s http://192.168.1.215:9000/comfy-gen/$file | \
    jq -r "select(.seed >= 10000 and .seed <= 20000) | .minio_url"
done
```

### Find validated generations above threshold

```bash
for file in $(curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.json'); do
  curl -s http://192.168.1.215:9000/comfy-gen/$file | \
    jq -r "select(.validation_score != null and .validation_score >= 0.8) | .minio_url"
done
```

## Future Enhancements

The metadata format enables future features:

- **CLI search tool** - `comfygen search --prompt "sunset" --min-score 0.8`
- **Experiment comparison** - Compare multiple generations side-by-side
- **Parameter analysis** - Identify which parameters produce best results
- **Reproducibility verification** - Automatically verify that re-runs produce identical results

## Technical Details

### Storage

- Metadata files are uploaded to the same MinIO bucket as images (`comfy-gen`)
- File naming: `<image_filename>.json` (e.g., `image.png` → `image.png.json`)
- Content type: `application/json`
- Public read access (via bucket policy)

### Implementation

Metadata creation happens in `generate.py`:

1. **Extract workflow parameters** - `extract_workflow_params()` reads KSampler settings
2. **Extract LoRAs** - `extract_loras_from_workflow()` finds all LoRA nodes
3. **Create metadata** - `create_metadata_json()` assembles the complete JSON
4. **Upload** - `upload_metadata_to_minio()` saves to MinIO after image upload

### Parameter Extraction

The system automatically extracts parameters from the workflow JSON:
- **Seed, steps, CFG** - From `KSampler` node
- **Sampler, scheduler** - From `KSampler` node inputs
- **LoRAs** - From all `LoraLoader` nodes in the workflow

## See Also

- [Validation Workflow](./VALIDATION.md) - Using validation scores in metadata
- [LoRA Injection](./LORA_INJECTION.md) - How LoRA metadata is captured
- [Presets](./PRESETS.md) - Using presets (tracked in metadata)
