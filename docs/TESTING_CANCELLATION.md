# Cancellation Feature Testing Guide

This document provides instructions for manually testing the new generation cancellation features.

## Prerequisites

- ComfyUI server running on moira (192.168.1.215:8188)
- Python environment with dependencies installed (`pip install -r requirements.txt`)
- Access to the repository from magneto or another development machine

## Test Cases

### Test 1: List Current Queue

**Purpose:** Verify the `--list` flag shows queue status correctly.

**Steps:**
```bash
python3 scripts/cancel_generation.py --list
```

**Expected Output:**
```
[INFO] Currently Running:
  - Prompt ID: <prompt_id>
[INFO] Queue (N items pending):
  - Prompt ID: <prompt_id>
  - Prompt ID: <prompt_id>
```

Or if empty:
```
[INFO] No items currently running
[INFO] Queue is empty
```

### Test 2: Cancel Current Generation

**Purpose:** Test interrupting the currently running generation.

**Steps:**
1. Start a long-running generation:
   ```bash
   python3 generate.py --workflow workflows/flux-dev.json \
       --prompt "detailed landscape" --output /tmp/test.png
   ```
2. In another terminal, run:
   ```bash
   python3 scripts/cancel_generation.py
   ```

**Expected Output:**
```
[OK] Interrupted current generation
```

**Verification:**
- The generation should stop on the ComfyUI server
- `generate.py` should exit or show an error

### Test 3: Cancel Specific Prompt by ID

**Purpose:** Test removing a specific job from the queue.

**Steps:**
1. Queue a generation and note the prompt ID:
   ```bash
   python3 generate.py --workflow workflows/flux-dev.json \
       --prompt "test prompt" --output /tmp/test.png
   ```
   (Note the "Queued workflow with ID: <prompt_id>" message)

2. Cancel it:
   ```bash
   python3 scripts/cancel_generation.py <prompt_id>
   ```

**Expected Output:**
```
[OK] Deleted prompt <prompt_id> from queue
```

**Verification:**
- Run `python3 scripts/cancel_generation.py --list` to confirm it's removed

### Test 4: Cancel via generate.py --cancel Flag

**Purpose:** Test the `--cancel` flag in generate.py.

**Steps:**
1. Queue a generation:
   ```bash
   python3 generate.py --workflow workflows/flux-dev.json \
       --prompt "test" --output /tmp/test.png
   ```

2. Cancel using generate.py:
   ```bash
   python3 generate.py --cancel <prompt_id>
   ```

**Expected Output:**
```
[OK] Cancelled generation <prompt_id>
[OK] Interrupted current generation
```

### Test 5: Ctrl+C During Generation

**Purpose:** Test graceful cancellation with keyboard interrupt.

**Steps:**
1. Start a generation:
   ```bash
   python3 generate.py --workflow workflows/flux-dev.json \
       --prompt "detailed artwork" --output /tmp/test.png
   ```

2. Press `Ctrl+C` while it's running

**Expected Output:**
```
^C
[WARN] Cancellation requested...
[INFO] Cancelling generation <prompt_id>...
[OK] Cancelled generation <prompt_id>
[OK] Interrupted current generation
[OK] Cancelled successfully
```

**Verification:**
- The script should exit cleanly (exit code 0)
- Any partial files should be cleaned up

### Test 6: Error Handling - Server Unreachable

**Purpose:** Test error handling when ComfyUI server is down.

**Steps:**
1. Stop ComfyUI server (or change COMFYUI_HOST to invalid)
2. Try to cancel:
   ```bash
   python3 scripts/cancel_generation.py
   ```

**Expected Output:**
```
[ERROR] Connection failed: <connection error details>
```

**Verification:**
- Script should exit with code 1
- Error message should be clear and helpful

### Test 7: Help Text Validation

**Purpose:** Verify all help text is correct and complete.

**Steps:**
```bash
python3 scripts/cancel_generation.py --help
python3 generate.py --help
```

**Expected Output:**
- Both should show clear usage instructions
- All flags should be documented
- Examples should be present in docstrings

## Success Criteria

All tests should:
- ✅ Exit with appropriate exit codes (0 for success, 1 for errors)
- ✅ Display clear messages using [OK], [ERROR], [INFO], [WARN] format
- ✅ Handle network errors gracefully
- ✅ Clean up resources on cancellation
- ✅ Not break existing functionality

## Notes

- The cancellation feature uses ComfyUI's native `/interrupt` and `/queue` endpoints
- Partial outputs are cleaned up using the `cleanup_partial_outputs()` function
- Signal handler is registered for graceful Ctrl+C handling
- All error messages follow the project convention (no emojis, ASCII only)
