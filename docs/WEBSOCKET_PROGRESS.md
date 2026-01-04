# WebSocket Progress Tracking

This document describes the real-time progress tracking feature added to `generate.py`.

## Overview

ComfyUI provides WebSocket updates during image/video generation. This feature connects to the WebSocket endpoint and displays real-time progress information including:

- Current step / total steps
- Estimated time remaining (ETA)
- Current node being executed
- Cached execution notifications

## Usage

### Basic Progress Tracking (Default)

By default, `generate.py` now displays real-time progress updates:

```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png
```

**Example Output:**
```
[INFO] Connected to progress stream
[INFO] Generation started
[PROGRESS] Sampling: 1/20 steps (5%) - ETA: 19s
[PROGRESS] Sampling: 5/20 steps (25%) - ETA: 12s
[PROGRESS] Sampling: 10/20 steps (50%) - ETA: 8s
[PROGRESS] Sampling: 15/20 steps (75%) - ETA: 4s
[PROGRESS] Sampling: 20/20 steps (100%) - ETA: 0s
[OK] Generation complete in 23.4s
```

### Quiet Mode

Suppress all progress output with the `--quiet` flag:

```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png \
    --quiet
```

This is useful when you only care about the final result URL.

### JSON Progress Mode

For agent consumption or script integration, use `--json-progress` to output machine-readable JSON:

```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png \
    --json-progress
```

**Example JSON Output:**
```json
{"step": 1, "max_steps": 20, "eta_seconds": 19.0, "node": "KSampler"}
{"step": 5, "max_steps": 20, "eta_seconds": 12.0, "node": "KSampler"}
{"step": 10, "max_steps": 20, "eta_seconds": 8.0, "node": "KSampler"}
{"step": 15, "max_steps": 20, "eta_seconds": 4.0, "node": "KSampler"}
{"step": 20, "max_steps": 20, "eta_seconds": 0.0, "node": "KSampler"}
```

Each line is a valid JSON object that can be parsed independently.

## Technical Details

### WebSocket Connection

The tracker connects to `ws://192.168.1.215:8188/ws` with a unique client ID.

### Events Handled

The ProgressTracker class handles the following ComfyUI WebSocket events:

| Event | Description | Action |
|-------|-------------|--------|
| `execution_start` | Generation started | Log start time and message |
| `executing` | Current node ID | Track current node |
| `progress` | Step progress within node | Display progress bar with ETA |
| `execution_cached` | Nodes were cached | Log cached node count |
| `executed` | Node completed | Log node completion |
| `execution_complete` | All done | Calculate and display total time |

### ETA Calculation

The ETA is calculated based on:
- Elapsed time since generation started
- Current step number
- Total steps required
- Time per step (elapsed / current_step)

Formula: `ETA = (max_steps - current_step) * (elapsed_time / current_step)`

## Implementation Details

### ProgressTracker Class

Located in `generate.py`, the `ProgressTracker` class:

1. Connects to WebSocket in a background thread
2. Listens for messages matching the prompt ID
3. Updates progress display in real-time
4. Calculates ETA based on elapsed time
5. Gracefully handles errors and connection issues

### Modified Functions

- `wait_for_completion()`: Now creates a ProgressTracker and uses WebSocket for real-time updates
- `run_generation()`: Accepts `quiet` and `json_progress` parameters
- `main()`: Adds `--quiet` and `--json-progress` CLI arguments

## For Agents

When calling `generate.py` from agents or scripts:

1. **Use `--json-progress`** for machine-readable output
2. **Parse each line separately** as a JSON object
3. **Monitor the `step` and `max_steps` fields** to show progress in your UI
4. **Use the `eta_seconds` field** to estimate completion time

Example Python code to consume JSON progress:

```python
import subprocess
import json

proc = subprocess.Popen(
    ["python3", "generate.py", "--workflow", "workflow.json", 
     "--prompt", "test", "--json-progress"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

for line in proc.stdout:
    try:
        data = json.loads(line)
        if "step" in data:
            print(f"Progress: {data['step']}/{data['max_steps']} - ETA: {data['eta_seconds']:.1f}s")
    except json.JSONDecodeError:
        pass  # Not a progress JSON line
```

## Backward Compatibility

The changes are fully backward compatible:
- Existing scripts work without modification
- Progress tracking is enabled by default but doesn't break existing workflows
- The `--quiet` flag can disable progress for legacy behavior

## Testing

Tests are available in `tests/test_websocket_progress.py`:

```bash
python3 tests/test_websocket_progress.py
```

All tests verify:
- ProgressTracker initialization
- Event handling
- Quiet mode behavior
- JSON output format
- Integration with `wait_for_completion()`
