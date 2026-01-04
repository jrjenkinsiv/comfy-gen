# Testing Guide

## Overview

This document describes the testing strategy for comfy-gen, including unit tests, integration tests, and manual validation procedures.

## Test Categories

### 1. Unit Tests (`tests/`)

Located in `tests/` directory, run with pytest:

```bash
pytest tests/ -v
pytest tests/test_generate.py -v  # Specific test file
pytest -k "test_lora" -v          # Tests matching pattern
```

**Coverage:**
- Workflow modification (`test_modify_prompt`, `test_inject_lora`)
- Parameter validation (`test_validate_generation_params`)
- LoRA chain injection (`test_inject_lora_chain`)
- Metadata creation (`test_create_metadata_json`)

### 2. MCP Tool Tests

Test MCP server tools in isolation:

```bash
# Start MCP server
python3 mcp_server.py

# Use MCP inspector (separate terminal)
npx @modelcontextprotocol/inspector python3 mcp_server.py
```

**Test each tool category:**
- Generation: `generate_image`, `img2img`, `text_to_video`
- Models: `list_models`, `list_loras`, `get_model_info`
- Gallery: `list_generations`, `filter_by_prompt`, `get_metadata`
- Prompts: `build_prompt`, `suggest_negative`, `analyze_prompt`
- Control: `cancel_generation`, `get_queue_status`

### 3. CLI Integration Tests

Test the full CLI workflow:

```bash
# Basic generation
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "test subject" --output /tmp/test.png \
    --steps 10 --width 512 --height 512

# With LoRA
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "anime girl" --lora "add-detail:0.8" \
    --output /tmp/test.png

# With validation
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "red car" --validate --auto-retry \
    --output /tmp/test.png
```

### 4. End-to-End Validation Tests

Full pipeline tests that validate output quality.

## Single Subject Generation Tests

**Problem:** Models tend to duplicate subjects (multiple cars, multiple people).

**Solution Strategy:**

1. **Use POSITIVE weighting** (more effective than negative prompts):
   ```
   (single Porsche 911:1.8) (one car only:1.5) (isolated vehicle:1.3)
   ```

2. **Strong negative prompts** for duplicates:
   ```
   multiple vehicles, duplicate cars, two cars, parking lot, car show, cloned, mirrored
   ```

3. **Composition hints**:
   ```
   centered composition, clean background, subject isolation
   ```

### Test Suite: Single Car Generation

Run the full test suite with varying parameters:

#### Test 1: Baseline (low steps, low emphasis)
```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "Porsche 911 red sports car on mountain road" \
    --negative-prompt "multiple cars, duplicate, two cars, parking lot, vehicle crowd" \
    --steps 20 --width 512 --height 512 --seed 5000 \
    --output /tmp/test_baseline.png
```

**Expected:** May still have duplicates at low steps

#### Test 2: High emphasis (positive weighting)
```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(single Porsche 911:1.8) (one car only:1.5), red sports car, mountain road, isolated vehicle, centered composition" \
    --negative-prompt "multiple vehicles, duplicate cars, two cars, three cars, parking lot, car show, vehicle crowd, cloned car, mirrored" \
    --steps 40 --width 1024 --height 1024 --seed 5001 \
    --output /tmp/test_high_emphasis.png
```

**Expected:** Single car with high confidence

#### Test 3: Ultra quality (50+ steps, HD resolution)
```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(single Porsche 911 GT3 RS:2.0) (only one car:1.6), racing red, professional automotive photography, isolated subject, centered composition, clean background, 8k ultra detail" \
    --negative-prompt "multiple vehicles, duplicate cars, two cars, three cars, parking lot, car show, vehicle crowd, cloned car, ghost car, reflected car, mirrored vehicles, convoy, traffic, bad quality, blurry, watermark" \
    --steps 50 --cfg 7.5 --width 1024 --height 1024 --seed 5002 \
    --sampler dpmpp_2m_sde --scheduler karras \
    --output /tmp/test_ultra.png
```

**Expected:** Single car, photorealistic, sharp details

#### Test 4: With validation and auto-retry
```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(single Porsche 911:1.8) (one car only:1.5), mountain road, professional photography" \
    --negative-prompt "multiple vehicles, duplicate cars, two cars, parking lot, vehicle crowd" \
    --steps 40 --width 1024 --height 1024 --seed 5003 \
    --validate --auto-retry --retry-limit 3 --positive-threshold 0.28 \
    --output /tmp/test_validated.png
```

**Expected:** Single car validated by CLIP score

### Test Matrix

| Test ID | Steps | Resolution | Positive Weight | Negative Strength | Expected Quality |
|---------|-------|------------|-----------------|-------------------|------------------|
| T1 | 20 | 512x512 | None | Basic | Low (may duplicate) |
| T2 | 40 | 1024x1024 | 1.5-1.8 | Strong | Good (single subject) |
| T3 | 50 | 1024x1024 | 1.8-2.0 | Very Strong | Excellent (guaranteed single) |
| T4 | 40 | 1024x1024 | 1.5 | Strong + CLIP validation | Very Good (validated) |

### Running Full Test Suite

```bash
# Create test script
cat > /tmp/run_single_subject_tests.sh << 'EOF'
#!/bin/bash
set -e

cd /Users/jrjenkinsiv/Development/comfy-gen
source .venv/bin/activate

echo "=== Single Subject Generation Test Suite ==="
echo ""

# Test 1: Baseline
echo "[Test 1/4] Baseline (20 steps, 512x512, no emphasis)"
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "Porsche 911 red sports car on mountain road" \
    --negative-prompt "multiple cars, duplicate, two cars, parking lot" \
    --steps 20 --width 512 --height 512 --seed 5000 \
    --output /tmp/test_baseline.png --no-validate

# Test 2: High emphasis
echo "[Test 2/4] High emphasis (40 steps, 1024x1024, weighted)"
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(single Porsche 911:1.8) (one car only:1.5), red sports car, mountain road" \
    --negative-prompt "multiple vehicles, duplicate cars, two cars, parking lot, vehicle crowd, cloned" \
    --steps 40 --width 1024 --height 1024 --seed 5001 \
    --output /tmp/test_high_emphasis.png --no-validate

# Test 3: Ultra quality
echo "[Test 3/4] Ultra quality (50 steps, 1024x1024, max weight)"
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(single Porsche 911 GT3 RS:2.0) (only one car:1.6), racing red, professional photography, isolated subject, centered composition" \
    --negative-prompt "multiple vehicles, duplicate cars, two cars, parking lot, car show, vehicle crowd, cloned car, mirrored" \
    --steps 50 --cfg 7.5 --width 1024 --height 1024 --seed 5002 \
    --sampler dpmpp_2m_sde --scheduler karras \
    --output /tmp/test_ultra.png --no-validate

# Test 4: With validation
echo "[Test 4/4] Validated (40 steps, 1024x1024, CLIP validation)"
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(single Porsche 911:1.8) (one car only:1.5), mountain road, professional photography" \
    --negative-prompt "multiple vehicles, duplicate cars, two cars, parking lot" \
    --steps 40 --width 1024 --height 1024 --seed 5003 \
    --output /tmp/test_validated.png --no-validate
    # Note: validation disabled due to numpy/torch compat issue

echo ""
echo "=== Test Results ==="
echo "Baseline:       http://192.168.1.215:9000/comfy-gen/$(ls -t /tmp/test_baseline.png* 2>/dev/null | head -1 | xargs -I{} basename {})"
echo "High emphasis:  http://192.168.1.215:9000/comfy-gen/$(ls -t /tmp/test_high_emphasis.png* 2>/dev/null | head -1 | xargs -I{} basename {})"
echo "Ultra quality:  http://192.168.1.215:9000/comfy-gen/$(ls -t /tmp/test_ultra.png* 2>/dev/null | head -1 | xargs -I{} basename {})"
echo "Validated:      http://192.168.1.215:9000/comfy-gen/$(ls -t /tmp/test_validated.png* 2>/dev/null | head -1 | xargs -I{} basename {})"
EOF

chmod +x /tmp/run_single_subject_tests.sh
/tmp/run_single_subject_tests.sh
```

## MCP vs CLI Parity Validation

### Feature Matrix

| Feature | CLI | MCP | Notes |
|---------|-----|-----|-------|
| Basic generation | ✅ | ✅ | generate.py vs generate_image() |
| Negative prompts | ✅ | ✅ | Both support |
| LoRA support | ✅ | ✅ | --lora vs loras param |
| Resolution control | ✅ | ✅ | --width/--height vs width/height |
| Steps/CFG/sampler | ✅ | ✅ | All params supported |
| Seed control | ✅ | ✅ | -1 for random |
| Img2img | ✅ | ✅ | --input-image vs img2img() |
| Text-to-video | ✅ | ✅ | wan2.2 support |
| Validation | ✅ | ⚠️  | CLI only (needs MCP integration) |
| Auto-retry | ✅ | ⚠️  | CLI only |
| Presets | ✅ | ❌ | CLI only |
| Metadata tracking | ✅ | ✅ | Both create .json sidecars |

### Validation Procedure

1. **Test same prompt with both interfaces:**

CLI:
```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "red Porsche 911" --steps 30 --width 512 --height 512 \
    --seed 1234 --output /tmp/cli_test.png
```

MCP (via inspector):
```json
{
  "tool": "generate_image",
  "args": {
    "prompt": "red Porsche 911",
    "steps": 30,
    "width": 512,
    "height": 512,
    "seed": 1234
  }
}
```

2. **Compare outputs:**
   - Visual similarity (should be identical with same seed)
   - Metadata completeness
   - Performance (generation time)

3. **Document discrepancies** and create issues for missing MCP features

## Continuous Integration

### Pre-commit checks

```bash
# Run before committing
pytest tests/ -v                    # Unit tests
ruff check . --fix                  # Linting
mypy comfygen/ --config-file pyproject.toml  # Type checking
python3 scripts/smoke_test.py      # Import validation
```

### GitHub Actions (future)

Automated testing on push:
- Lint and type check
- Unit tests
- Model availability check
- MCP tool smoke tests

## Known Issues

1. **Validation dependencies:** NumPy 2.x/torch compatibility issue prevents CLIP validation
   - **Workaround:** Use `--no-validate` flag
   - **Fix:** `pip install numpy<2` or upgrade torch

2. **Multiple subjects:** Standard negative prompts fail to prevent duplicates
   - **Solution:** Use positive weighting `(single:1.8)` + strong vehicle-specific negatives
   - **See:** This document's single subject test suite

3. **MCP validation:** Missing validation/retry features in MCP tools
   - **Status:** Tracked for future implementation
   - **Workaround:** Use CLI for quality-critical generations

## Documentation Updates

After running tests, update:

1. **MODEL_REGISTRY.md** - If new models/LoRAs tested
2. **AGENT_GUIDE.md** - Add new prompt engineering findings
3. **MCP_COMPREHENSIVE.md** - Document MCP tool updates
4. **This file (TESTING.md)** - Add new test cases

## Memory Updates

Create/update memory file for agent context:

```bash
cat > ~/.vscode-copilot/memories/comfy-gen-pipeline.md << 'EOF'
# ComfyGen Local Pipeline

## When user says "generate image/video"

**ALWAYS use the local ComfyGen pipeline:**

```bash
cd /Users/jrjenkinsiv/Development/comfy-gen
source .venv/bin/activate
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "USER_PROMPT" \
    --negative-prompt "SPECIFIC_TO_SUBJECT" \
    --output /tmp/output.png
```

**DO NOT suggest:**
- External services (DALL-E, Midjourney, etc.)
- Cloud APIs
- Web-based generators

**Infrastructure:**
- ComfyUI server: moira (192.168.1.215:8188)
- MinIO storage: http://192.168.1.215:9000/comfy-gen/
- GPU: RTX 5090 on moira

**For single subject (car, person, object):**
- Use positive weighting: `(single SUBJECT:1.8) (one SUBJECT only:1.5)`
- Use subject-specific negative prompts (see presets.yaml)
- Prefer 40-50 steps at 1024x1024 for quality

**For video:**
- Use wan2.2 workflows in `workflows/wan/`
- Text-to-video or image-to-video supported
EOF
```
