# Battleship Sprite Generation - Quality Issues & Solutions

## Problem: Validation Passes But Images Look Bad

### How CLIP Validation Actually Works

The `--validate` flag uses **CLIP (Contrastive Language-Image Pre-training)** to check semantic similarity:

```
1. Load image and prompt text
2. Compute embeddings using CLIP model
3. Calculate cosine similarity score (0-1)
4. Pass if score > threshold (default: 0.25)
```

**What CLIP checks:**
- ✅ "Does the image semantically match the prompt?"
- ✅ "Is there a battleship in the image?"

**What CLIP DOES NOT check:**
- ❌ Perspective (top-down vs side view vs isometric)
- ❌ Image quality, sharpness, artifacts
- ❌ Compositional requirements (flat vs 3D)
- ❌ Style accuracy (pixel art vs realistic)
- ❌ Whether it's usable for your game

### Why Threshold is Too Low

Default threshold: **0.25** (25% similarity)
- This is extremely permissive
- Any image with vague battleship shapes passes
- Even wrong angles pass if they contain naval themes

### Solution 1: Increase Sampling Steps

**Current:** 30 steps (default)  
**Problem:** Not enough iterations for quality convergence

**Recommended:**
```bash
--steps 50   # Good balance (15-20 seconds)
--steps 80   # High quality (25-30 seconds)
--steps 100  # Maximum quality (35-40 seconds)
```

**Why this helps:**
- More diffusion iterations = better convergence
- Cleaner lines and details
- Better adherence to prompt constraints

### Solution 2: Stricter Validation Threshold

**Adjust the positive threshold:**
```bash
--positive-threshold 0.7   # Moderately strict
--positive-threshold 0.85  # Strict
--positive-threshold 0.95  # Very strict (may retry often)
```

**Combined with auto-retry:**
```bash
--validate --auto-retry --retry-limit 5 --positive-threshold 0.85
```

This forces regeneration until semantic similarity is very high.

### Solution 3: Improved Prompt Engineering

**Problem prompts:**
```
"battleship bow section, top-down view, game sprite"
```

This is too vague. CLIP doesn't understand "top-down" as a strict requirement.

**Better prompts:**
```
"battleship bow section viewed from DIRECTLY ABOVE, 
looking straight down, zero angle, perfectly flat 2D,
no perspective whatsoever, pure orthographic projection,
like a board game token, architectural floor plan view,
absolutely flat as paper, no depth cues"
```

**Why this works:**
- Multiple reinforcing phrases for the same concept
- Strong negation of unwanted features
- Reference to familiar visual concepts (board game, floor plan)

### Solution 4: Reference Images (Not Yet Supported)

**Ideal workflow (future feature):**
1. Generate one good top-down sprite manually
2. Use it as validation reference
3. Compare future generations to the reference image
4. Only accept if visually similar to reference

**This would require:**
- Image-to-image CLIP comparison
- Not just text-to-image similarity
- Feature request for future enhancement

### Solution 5: Manual Cherry-Picking (Recommended)

**Current best practice:**

1. **Generate multiple candidates** (4-6 variations)
   ```bash
   for i in {1..6}; do
     python3 generate.py --workflow workflows/flux-dev.json \
       --steps 80 \
       --prompt "your optimized prompt here" \
       --output /tmp/battleship_candidate_${i}.png
   done
   ```

2. **Review all candidates visually**
   - Open in browser: http://192.168.1.215:9000/comfy-gen/
   - Compare side-by-side
   - Select best 1-2 manually

3. **No validation needed for manual review**
   - Your eyes are better than CLIP for this use case
   - CLIP can't judge "good game sprite art"

### Recommended Generation Command

**For battleship sprites specifically:**

```bash
python3 generate.py \
  --workflow workflows/flux-dev.json \
  --steps 80 \
  --cfg 8.5 \
  --prompt "battleship bow section, viewed from DIRECTLY OVERHEAD, pure flat 2D, zero perspective, zero depth, architectural plan view, board game piece, perfectly orthographic, like looking through a telescope from space, no angle whatsoever, flat as paper, game sprite token" \
  --negative-prompt "3D, perspective, any angle, side view, diagonal, isometric, depth, shadow, realistic lighting, photographic, tilted, angled, oblique, foreshortening, vanishing point, people, water, ocean, text" \
  --output /tmp/battleship_bow_test.png
```

**Parameters explained:**
- `--steps 80` - More iterations for quality
- `--cfg 8.5` - Slightly higher guidance (follows prompt closer)
- Redundant positive prompt phrases for emphasis
- Comprehensive negative prompts

### When to Use Validation

**Good use cases:**
- Detecting completely wrong subjects (car instead of ship)
- Filtering out corrupted/broken images
- Batch processing where some images fail completely

**Bad use cases:**
- Ensuring specific perspective/angle
- Judging artistic quality
- Checking for game sprite suitability
- Verifying "good enough" results

### Future Improvements

Possible enhancements to validation system:

1. **Multi-prompt validation:**
   ```python
   must_match = ["top-down view", "flat 2D", "board game piece"]
   must_not_match = ["side view", "3D render", "perspective"]
   ```

2. **Edge detection checks:**
   - Verify low variance in vertical axis (flat projection)
   - Detect horizon lines (indicates perspective)

3. **Reference image comparison:**
   - Provide example of "good" sprite
   - Calculate perceptual similarity (SSIM, LPIPS)

4. **Custom CLIP prompts:**
   - Separate validation prompt from generation prompt
   - Example: Validate against "flat orthographic game token" even if generation uses different phrasing

## Immediate Action Items

1. ✅ Increase steps to 80+
2. ✅ Strengthen positive prompts with redundant phrasing
3. ✅ Generate 4-6 candidates per variant
4. ✅ Manually review and select best results
5. ⚠️ Use validation only to catch broken images
6. ⚠️ Don't rely on validation for perspective/quality

## Example Session

```bash
# Generate 4 candidates with high quality settings
for i in {1..4}; do
  python3 generate.py \
    --workflow workflows/flux-dev.json \
    --steps 80 \
    --cfg 8.5 \
    --prompt "battleship bow, DIRECTLY OVERHEAD view, pure flat 2D, zero perspective, architectural plan, board game token, perfectly orthographic, flat as paper" \
    --negative-prompt "3D, perspective, angle, side view, diagonal, isometric, depth, shadow, people, water" \
    --output /tmp/bow_candidate_${i}.png
done

# Review manually
open "http://192.168.1.215:9000/comfy-gen/"

# Select best candidate and rename
cp /tmp/bow_candidate_3.png /tmp/battleship_bow_final.png
```

No validation needed - your judgment is the validation.
