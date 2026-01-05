# Testing Guide

## Overview

This document describes the testing strategy for comfy-gen, including unit tests, integration tests, and manual validation procedures.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_validation.py -v

# Run tests matching pattern
pytest -k "test_lora" -v

# Run manual tests (require local network)
python3 tests/manual_test_prompt_presets.py
python3 tests/manual_test_transparent.py
```

## Test Files

| File | Purpose | Network Required | Notes |
|------|---------|------------------|-------|
| `test_validation.py` | CLIP validation, YOLO person counting | No | Uses mocks for missing files |
| `test_quality.py` | Image quality scoring (pyiqa) | No | Gracefully handles missing pyiqa |
| `test_generate.py` | Server availability, error handling | No | Mocked server responses |
| `test_lora_injection.py` | LoRA chain injection logic | No | Mocked file I/O |
| `test_metadata.py` | Metadata extraction, workflow params | No | Mocked local network calls |
| `test_prompt_enhancer.py` | Prompt enhancement fallback | No | Mocked transformers |
| `test_advanced_params.py` | Advanced parameter validation | No | Mocked workflows |
| `test_integration_params.py` | Parameter integration tests | No | Mocked ComfyUI API |
| `test_websocket_progress.py` | WebSocket progress tracking | No | Mocked WebSocket |
| `test_config_loader.py` | Config file loading | No | Uses temp files |
| `test_prompt_presets.py` | Preset loading and validation | No | Mocked file I/O |
| `test_transparent.py` | Transparent image generation | No | Mocked ComfyUI API |
| `test_refinement.py` | Image refinement workflows | No | Mocked workflows |
| `test_mcp_server.py` | MCP server tool registration | No | Async tool listing only |
| `test_mcp_presets.py` | MCP preset tools | No | Mocked presets |
| `test_mcp_validation.py` | MCP validation tools | Yes | Requires local ComfyUI server |
| `test_comprehensive_mcp.py` | Full MCP workflow | Yes | Requires ComfyUI + MinIO |
| `test_civitai_mcp.py` | CivitAI MCP tools | Internet | Requires CivitAI API access |
| `test_civitai_integration.py` | CivitAI API integration | Internet | Real API calls |
| `test_huggingface_mcp.py` | HuggingFace MCP tools | Internet | Requires HF API access |
| `test_quality_integration.py` | Quality scoring integration | Yes | Requires real images |
| `test_metadata_backward_compat.py` | Metadata backward compatibility | No | Uses sample data |
| `test_metadata_embedding.py` | PNG metadata embedding | No | Creates temp images |
| `test_metadata_schema_example.py` | Metadata schema examples | No | Documentation test |
| `test_progress_tracking.py` | Generation progress tracking | No | Mocked WebSocket |
| `manual_test_prompt_presets.py` | Manual preset testing | Yes | Requires ComfyUI server |
| `manual_test_transparent.py` | Manual transparency test | Yes | Requires ComfyUI server |

## Test Strategy

### Unit Tests
- **Scope:** Individual functions and classes in isolation
- **Mocking:** Extensive use of `unittest.mock` for external dependencies
- **Network:** No network access required
- **CI:** Can run in CI environment (GitHub Actions)

### Integration Tests
- **Scope:** Multiple components working together
- **Mocking:** Minimal - tests real interactions between components
- **Network:** May require local ComfyUI server and MinIO
- **CI:** Run on self-hosted runner with local network access

### Manual Tests
- **Scope:** Full end-to-end workflows requiring human verification
- **Mocking:** None - uses real ComfyUI API and generates actual images
- **Network:** Requires local network access to ComfyUI server (default: 192.168.1.215:8188, configurable via `COMFY_SERVER_ADDRESS` environment variable)
- **CI:** Not suitable for automated CI

### External API Tests
- **Scope:** CivitAI and HuggingFace integrations
- **Mocking:** None for integration tests, mocked for unit tests
- **Network:** Requires internet access
- **CI:** Can run in CI with API keys in secrets

## Mocking Strategy

### ComfyUI API
- **Tool:** `unittest.mock.patch` with `requests.get`/`requests.post`
- **Mock Responses:** Simulated queue status, generation results, system stats
- **Example:**
  ```python
  with patch('requests.post') as mock_post:
      mock_post.return_value.json.return_value = {"prompt_id": "test-123"}
      result = queue_workflow(workflow, server_address)
  ```

### MinIO
- **Tool:** `unittest.mock` for MinIO client operations
- **Mock Operations:** Bucket listing, file uploads, URL generation
- **Note:** No dedicated MinIO mocking library used (e.g., moto is for AWS S3)
- **Example:**
  ```python
  with patch('minio.Minio') as mock_minio:
      mock_client = mock_minio.return_value
      mock_client.bucket_exists.return_value = True
  ```

### File System
- **Tool:** `tempfile` module for temporary files/directories
- **Strategy:** Create real temp files for I/O tests, clean up automatically
- **Example:**
  ```python
  with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
      test_image_path = tmp.name
      # Test code using test_image_path
  ```

### Transformers/ML Models
- **Tool:** `unittest.mock.patch` for model loading and inference
- **Strategy:** Mock model outputs to avoid downloading large models in tests
- **Example:**
  ```python
  with patch('transformers.pipeline') as mock_pipeline:
      mock_pipeline.return_value.return_value = [{"generated_text": "enhanced prompt"}]
  ```

## CI Integration

### Current Setup
- **Platform:** GitHub Actions with self-hosted runner (ant-man)
- **Runner:** ARM64 Linux with local network access
- **Workflow:** `.github/workflows/generate.yml`

### Test Execution in CI
Currently, CI focuses on generation workflows rather than running pytest. Future CI improvements could include:

```yaml
# Future CI test job (proposed)
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run Unit Tests
        run: |
          pytest tests/ -v -m "not network_required"
      
      - name: Run Integration Tests (Local Network)
        if: runner.name == 'ant-man'  # Self-hosted runner only
        run: |
          pytest tests/ -v -m "network_required"
```

### Test Markers (Proposed)
To enable selective test execution, tests could be marked with pytest markers:

```python
# Example marker usage (not currently implemented):
import pytest

@pytest.mark.network_required
def test_comfyui_api():
    """Test that requires local ComfyUI server."""
    pass

@pytest.mark.internet_required
def test_civitai_api():
    """Test that requires internet access."""
    pass
```

### Pre-commit Checks
```bash
# Run before committing (no network required)
# Note: Marker-based filtering not yet implemented, run all tests or specific files
pytest tests/test_validation.py tests/test_quality.py tests/test_generate.py -v
ruff check . --fix
mypy comfygen/ --config-file pyproject.toml
```

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
