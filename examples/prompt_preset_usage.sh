#!/bin/bash
# Example usage of --prompt-preset flag
# These examples demonstrate the new prompt preset feature

echo "========================================"
echo "PROMPT PRESET FEATURE EXAMPLES"
echo "========================================"

# Example 1: List all available presets
echo ""
echo "Example 1: List available presets"
echo "Command: python3 generate.py --list-presets"
echo ""
python3 generate.py --list-presets

# Example 2: Use a preset (requires ComfyUI server)
echo ""
echo "Example 2: Use a complete preset"
echo "Command: python3 generate.py --workflow workflows/flux-dev.json --prompt-preset nude_woman_garden --output /tmp/test.png"
echo "(This would run generation if ComfyUI server is available)"
echo ""

# Example 3: Override preset prompt
echo ""
echo "Example 3: Override preset positive prompt"
echo "Command: python3 generate.py --workflow workflows/flux-dev.json --prompt-preset nude_woman_garden --prompt 'custom prompt' --output /tmp/test.png"
echo "(This would use the custom prompt but still use the preset's negative prompt)"
echo ""

# Example 4: Add to preset negative
echo ""
echo "Example 4: Merge additional negative terms with preset"
echo "Command: python3 generate.py --workflow workflows/flux-dev.json --prompt-preset nude_woman_garden --negative-prompt 'extra terms' --output /tmp/test.png"
echo "(This would merge 'extra terms' with the preset's negative prompt)"
echo ""

# Example 5: Invalid preset
echo ""
echo "Example 5: Try using non-existent preset (should fail gracefully)"
echo "Command: python3 generate.py --workflow workflows/flux-dev.json --prompt-preset nonexistent"
echo ""
python3 generate.py --workflow workflows/flux-dev.json --prompt-preset nonexistent 2>&1 | grep -A 2 "ERROR"

echo ""
echo "========================================"
echo "Feature demonstration complete"
echo "========================================"
