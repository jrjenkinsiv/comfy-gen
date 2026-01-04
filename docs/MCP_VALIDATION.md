# MCP CLIP Validation Flow

This document describes how CLIP validation works in the MCP `generate_image` tool.

## Validation Flow

```
┌─────────────────────────────────────────────────────────────┐
│ MCP Client calls generate_image()                          │
│ - prompt: "single red car"                                  │
│ - validate: True (default)                                  │
│ - auto_retry: True (default)                                │
│ - retry_limit: 3 (default)                                  │
│ - positive_threshold: 0.25 (default)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Attempt 1             │
         │ - Generate image      │
         │ - Queue to ComfyUI    │
         │ - Wait for completion │
         └───────┬───────────────┘
                 │
                 ▼
         ┌───────────────────────┐
         │ Download image        │
         │ for validation        │
         └───────┬───────────────┘
                 │
                 ▼
         ┌───────────────────────────────┐
         │ Run CLIP validation           │
         │ - Load image                  │
         │ - Compute similarity score    │
         │ - Compare to threshold        │
         └───────┬───────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ Score >= 0.25? │
         └───────┬────────┘
                 │
        ┌────────┴────────┐
        │                 │
       YES               NO
        │                 │
        ▼                 ▼
  ┌─────────┐      ┌──────────────┐
  │ SUCCESS │      │ auto_retry?  │
  │ Return  │      └──────┬───────┘
  │ result  │             │
  └─────────┘      ┌──────┴──────┐
                   │             │
                  YES           NO
                   │             │
                   ▼             ▼
           ┌───────────────┐  ┌──────────┐
           │ Adjust prompt │  │ FAILURE  │
           │ - Increase    │  │ Return   │
           │   weights     │  │ with low │
           │ - Add negative│  │ score    │
           │   terms       │  └──────────┘
           └───────┬───────┘
                   │
                   ▼
           ┌───────────────┐
           │ Attempt 2     │
           │ (same flow)   │
           └───────┬───────┘
                   │
                   ▼
           ┌───────────────┐
           │ Continue until│
           │ success or    │
           │ max retries   │
           └───────────────┘
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `validate` | bool | `True` | Run CLIP validation after generation |
| `auto_retry` | bool | `True` | Automatically retry if validation fails |
| `retry_limit` | int | `3` | Maximum number of retry attempts |
| `positive_threshold` | float | `0.25` | Minimum CLIP score to pass validation |

## Response Format

### Success with Validation Passed
```json
{
  "status": "success",
  "url": "http://192.168.1.215:9000/comfy-gen/20260104_102345_output.png",
  "prompt_id": "abc123",
  "attempt": 1,
  "validation": {
    "passed": true,
    "positive_score": 0.342,
    "negative_score": 0.124,
    "score_delta": 0.218,
    "reason": "Image passed validation"
  },
  "metadata": { ... }
}
```

### Success with Validation Failed (Max Retries)
```json
{
  "status": "success",
  "url": "http://192.168.1.215:9000/comfy-gen/20260104_102345_output.png",
  "prompt_id": "abc123",
  "attempt": 3,
  "validation": {
    "passed": false,
    "positive_score": 0.218,
    "reason": "Low positive CLIP score: 0.218 < 0.25",
    "warning": "Max retries (3) reached"
  },
  "metadata": { ... }
}
```

### Validation Disabled
```json
{
  "status": "success",
  "url": "http://192.168.1.215:9000/comfy-gen/20260104_102345_output.png",
  "prompt_id": "abc123",
  "metadata": { ... }
}
```

## Prompt Adjustment on Retry

When validation fails and `auto_retry=True`, the system automatically adjusts prompts:

**Original Prompt:** `"single car on a road"`

**Attempt 1:** `"single car on a road"` → Validation fails (score: 0.22)

**Attempt 2:** `"(single car:1.3) on a road"` (weight increased)
- Negative prompt adds: `"multiple cars, duplicate, cloned, ghosting, mirrored, two cars, extra car"`

**Attempt 3:** `"(single car:1.6) on a road"` (weight increased further)

This automatic adjustment helps address common validation failures like:
- Multiple subjects when one is requested
- Wrong subject in image
- Low semantic similarity to prompt

## Usage Examples

### Basic Usage (Defaults)
```python
result = await generate_image(
    prompt="single red car on a country road",
    negative_prompt="multiple cars, blurry"
    # validate=True, auto_retry=True by default
)
```

### Disable Validation
```python
result = await generate_image(
    prompt="landscape with mountains",
    validate=False
)
```

### Custom Validation Settings
```python
result = await generate_image(
    prompt="single cat sitting on a windowsill",
    validate=True,
    auto_retry=True,
    retry_limit=5,  # More retries
    positive_threshold=0.30  # Stricter threshold
)
```

## Implementation Details

The validation implementation:
1. **Reuses CLI validation code** from `comfy_gen.validation` module
2. **Downloads images temporarily** for validation (cleaned up after)
3. **Adjusts prompts automatically** using regex to increase emphasis weights
4. **Returns full validation details** in the response
5. **Handles missing dependencies gracefully** (falls back if CLIP not installed)

## Testing

Run the test suite:
```bash
python3 tests/test_mcp_validation.py
```

Run usage examples:
```bash
python3 examples/mcp_validation_example.py
```
