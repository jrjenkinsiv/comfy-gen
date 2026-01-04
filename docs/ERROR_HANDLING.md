# Error Handling and Validation Guide

This document describes the error handling, model validation, and dry-run features added to `generate.py`.

## Overview

The script now includes robust error handling to gracefully manage common failure scenarios:

- ComfyUI server unavailability
- Missing or invalid models
- Network failures and timeouts
- Invalid workflow files
- Missing input files

## Exit Codes

The script now returns meaningful exit codes:

- `0` - Success (EXIT_SUCCESS)
- `1` - Generation or runtime failure (EXIT_FAILURE)
- `2` - Configuration error (EXIT_CONFIG_ERROR)

Examples of config errors:
- Server is not available
- Workflow file not found or invalid JSON
- Required models are missing
- Input image file not found

## Server Availability Check

Before attempting any generation, the script checks if the ComfyUI server is reachable:

```bash
python3 generate.py --workflow workflows/flux-dev.json --prompt "test"
```

If the server is down, you'll see:
```
[ERROR] Cannot connect to ComfyUI server at http://192.168.1.215:8188
[ERROR] Make sure ComfyUI is running on moira (192.168.1.215:8188)
[ERROR] ComfyUI server is not available
```

Exit code: `2` (config error)

## Model Validation

The script queries available models from the ComfyUI API and validates that all models referenced in the workflow exist:

```bash
python3 generate.py --workflow workflows/flux-dev.json --prompt "test"
```

If models are missing:
```
[ERROR] Workflow validation failed - missing models:
  - checkpoint: missing-model.safetensors
    Suggested fallbacks:
      * sd15-v1-5.safetensors
      * sdxl-base-1.0.safetensors
```

Exit code: `2` (config error)

## Dry-Run Mode

Use `--dry-run` to validate a workflow without generating images:

```bash
python3 generate.py --workflow workflows/flux-dev.json --dry-run
```

This will:
1. Check server availability
2. Load and parse the workflow file
3. Validate all models exist
4. Report success or failure

If successful:
```
[OK] ComfyUI server is available
[OK] Retrieved available models from server
[OK] Workflow validation passed - all models available
[OK] Dry-run mode - workflow is valid
[OK] Workflow: workflows/flux-dev.json
[OK] Validation complete - no generation performed
```

Exit code: `0` (success)

**Note:** When using `--dry-run`, the `--prompt` argument is optional since no generation occurs.

## Retry Logic

The script now includes automatic retry with exponential backoff for transient failures:

- Maximum retries: 3 (configurable via `MAX_RETRIES`)
- Initial delay: 2 seconds (configurable via `RETRY_DELAY`)
- Backoff multiplier: 2x (configurable via `RETRY_BACKOFF`)

The retry logic applies to:
- Server errors (HTTP 5xx)
- Connection errors
- Timeout errors

Client errors (HTTP 4xx) are NOT retried as they indicate invalid requests.

Example output:
```
[ERROR] Failed to queue workflow: HTTP 503
[ERROR] Response: Service Unavailable
[INFO] Retrying in 2 seconds... (attempt 1/3)
```

## Error Message Format

All error messages use the `[ERROR]` prefix with no emojis (for Windows compatibility):

```
[ERROR] Cannot connect to ComfyUI server at http://192.168.1.215:8188
[ERROR] Workflow file not found: nonexistent.json
[ERROR] Invalid JSON in workflow file: Expecting ',' delimiter: line 5 column 3 (char 45)
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
python3 tests/test_generate.py
```

This tests:
- Server availability checking
- Model querying and validation
- Retry logic
- Exit codes
- Error handling

### Manual Integration Tests

Run the manual test script:

```bash
bash tests/test_error_handling_manual.sh
```

This tests real-world scenarios:
- Server availability check
- Missing workflow files
- Invalid JSON workflows
- Missing prompts
- Help text

## Common Scenarios

### Scenario 1: Server is down

**Command:**
```bash
python3 generate.py --workflow workflows/flux-dev.json --prompt "a cat"
```

**Output:**
```
[ERROR] Cannot connect to ComfyUI server at http://192.168.1.215:8188
[ERROR] Make sure ComfyUI is running on moira (192.168.1.215:8188)
[ERROR] ComfyUI server is not available
```

**Exit Code:** 2

**Solution:** Start the ComfyUI server on moira

### Scenario 2: Missing model in workflow

**Command:**
```bash
python3 generate.py --workflow workflows/custom.json --prompt "a dog"
```

**Output:**
```
[OK] ComfyUI server is available
[OK] Retrieved available models from server
[ERROR] Workflow validation failed - missing models:
  - checkpoint: custom-model-v2.safetensors
    Suggested fallbacks:
      * custom-model-v1.safetensors
      * sd15-v1-5.safetensors
```

**Exit Code:** 2

**Solution:** Update the workflow to use an available model or download the missing model

### Scenario 3: Transient network error

**Command:**
```bash
python3 generate.py --workflow workflows/flux-dev.json --prompt "a bird"
```

**Output:**
```
[OK] ComfyUI server is available
[OK] Retrieved available models from server
[OK] Workflow validation passed - all models available
Updated positive prompt in node 2
Updated negative prompt in node 3
[ERROR] Connection error: Connection reset by peer
[INFO] Retrying in 2 seconds... (attempt 1/3)
Queued workflow with ID: abc123-def456
```

**Exit Code:** 0 (if retry succeeds)

**Solution:** None needed - automatic retry handled it

### Scenario 4: Validate workflow before generation

**Command:**
```bash
python3 generate.py --workflow workflows/new-workflow.json --dry-run
```

**Output:**
```
[OK] ComfyUI server is available
[OK] Retrieved available models from server
[OK] Workflow validation passed - all models available
[OK] Dry-run mode - workflow is valid
[OK] Workflow: workflows/new-workflow.json
[OK] Validation complete - no generation performed
```

**Exit Code:** 0

**Next Step:** Run the actual generation without `--dry-run`

## Configuration

You can adjust retry behavior by modifying constants in `generate.py`:

```python
# Retry configuration
MAX_RETRIES = 3              # Maximum retry attempts
RETRY_DELAY = 2              # Initial delay in seconds
RETRY_BACKOFF = 2            # Exponential backoff multiplier
```

For example, to retry 5 times with a 5-second initial delay:
```python
MAX_RETRIES = 5
RETRY_DELAY = 5
```

## API Reference

### New Functions

#### `check_server_availability()`
Checks if ComfyUI server is reachable.

**Returns:** `bool` - True if server is available, False otherwise

#### `get_available_models()`
Queries available models from ComfyUI API.

**Returns:** `dict` - Dictionary of available models by type (checkpoints, loras, vae), or None on failure

#### `find_model_fallbacks(requested_model, available_models, model_type)`
Suggests fallback models when requested model is not found.

**Parameters:**
- `requested_model` (str) - The model that was requested
- `available_models` (dict) - Dictionary of available models
- `model_type` (str) - Type of model ("checkpoints", "loras", "vae")

**Returns:** `list` - List of suggested fallback models (up to 5)

#### `validate_workflow_models(workflow, available_models)`
Validates that all models referenced in workflow exist.

**Parameters:**
- `workflow` (dict) - The workflow dictionary
- `available_models` (dict) - Dictionary of available models

**Returns:** `tuple` - (is_valid, missing_models, suggestions)
- `is_valid` (bool) - True if all models exist
- `missing_models` (list) - List of (model_type, model_name) tuples
- `suggestions` (dict) - Dict mapping model names to suggested alternatives

### Modified Functions

#### `queue_workflow(workflow, retry=True)`
Now includes retry logic with exponential backoff.

**Parameters:**
- `workflow` (dict) - The workflow dictionary
- `retry` (bool) - Whether to retry on transient failures (default: True)

**Returns:** `str` - prompt_id on success, None on failure

## Troubleshooting

### Issue: "Cannot connect to ComfyUI server"

**Cause:** ComfyUI server is not running or not accessible

**Solution:**
1. SSH to moira: `ssh moira`
2. Check if ComfyUI is running: `tasklist | findstr python`
3. Start ComfyUI: `python C:\Users\jrjen\comfy-gen\scripts\start_comfyui.py`

### Issue: "Workflow validation failed"

**Cause:** Workflow references models that don't exist on the server

**Solution:**
1. Check the suggested fallbacks in the error message
2. Update the workflow JSON to use an available model, OR
3. Download the missing model to the appropriate directory on moira

### Issue: "Invalid JSON in workflow file"

**Cause:** Workflow file contains malformed JSON

**Solution:**
1. Validate JSON syntax using a JSON validator
2. Fix syntax errors (missing commas, quotes, brackets)
3. Re-export workflow from ComfyUI if necessary

### Issue: Retries exhausted but still failing

**Cause:** Persistent server issue or network problem

**Solution:**
1. Check ComfyUI server logs for errors
2. Verify network connectivity to moira
3. Restart ComfyUI server if needed
4. Contact system administrator if problem persists
