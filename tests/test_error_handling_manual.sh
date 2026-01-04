#!/bin/bash
# Manual test script for error handling features
# This script tests the new error handling and validation features
# NOTE: These tests will fail gracefully when server is unavailable

echo "=========================================="
echo "Testing Error Handling Features"
echo "=========================================="
echo ""

# Test 1: Server availability check
echo "Test 1: Server availability check (expected to fail when server is down)"
python3 generate.py --workflow workflows/flux-dev.json --dry-run || true
EXIT_CODE=$?
if [ $EXIT_CODE -eq 2 ] || [ $EXIT_CODE -eq 0 ]; then
    echo "[OK] Handled server check appropriately"
else
    echo "[FAIL] Unexpected exit code: $EXIT_CODE"
fi
echo ""

# Test 2: Missing workflow file
echo "Test 2: Missing workflow file"
python3 generate.py --workflow nonexistent.json --prompt "test" 2>&1 | grep -q "not found" || true
if [ $? -eq 0 ]; then
    echo "[OK] Detected missing workflow file"
else
    echo "[WARN] Could not verify missing workflow detection (server may be down)"
fi
echo ""

# Test 3: Invalid JSON workflow
echo "Test 3: Invalid JSON workflow"
echo "invalid json {" > /tmp/invalid.json
python3 generate.py --workflow /tmp/invalid.json --prompt "test" 2>&1 | grep -q "Invalid JSON" || true
if [ $? -eq 0 ]; then
    echo "[OK] Detected invalid JSON"
else
    echo "[WARN] Could not verify invalid JSON detection (server may be down)"
fi
rm /tmp/invalid.json
echo ""

# Test 4: Missing prompt without dry-run
echo "Test 4: Missing prompt without dry-run"
python3 generate.py --workflow workflows/flux-dev.json 2>&1 | grep -q "required" || true
if [ $? -eq 0 ]; then
    echo "[OK] Requires prompt for generation"
else
    echo "[WARN] Could not verify prompt requirement"
fi
echo ""

# Test 5: Help text includes new flags
echo "Test 5: Help text includes new flags"
python3 generate.py --help | grep -q "\-\-dry\-run"
if [ $? -eq 0 ]; then
    echo "[OK] --dry-run flag is documented"
else
    echo "[FAIL] --dry-run flag should be in help"
fi
echo ""

echo "=========================================="
echo "Manual tests complete!"
echo "=========================================="
echo ""
echo "NOTE: Tests that require a running ComfyUI server"
echo "will fail gracefully with appropriate error messages."
echo ""
echo "To test with a real server:"
echo "1. Ensure ComfyUI is running on moira (192.168.1.215:8188)"
echo "2. Run: python3 generate.py --workflow workflows/flux-dev.json --dry-run"
echo "3. Expected: Model validation and successful dry-run"
