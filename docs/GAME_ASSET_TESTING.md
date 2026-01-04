# Game Asset LoRA Testing Guide

This guide provides step-by-step instructions for downloading and testing the game asset LoRAs identified in the research phase.

**Prerequisites:**
- Access to moira (192.168.1.215)
- ComfyUI running on moira
- RTX 5090 GPU available
- MinIO configured for output storage

## Download Instructions

### 1. Icons & Flat Design LoRAs

#### Flux LoRA - Flat Art Style Game Assets
```bash
# SSH to moira
ssh moira
cd C:\Users\jrjen\comfy\models\loras

# Download from CivitAI
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "flux_flat_art_game_assets.safetensors"
```
**CivitAI Link:** https://civitai.com/models/1039062/flux-lora-flat-art-style-game-assets  
**Version:** Latest (check page for version ID)  
**Size:** ~100-200 MB

#### Simple Vector Flux
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "simple_vector_flux.safetensors"
```
**CivitAI Link:** https://civitai.com/models/785122/simple-vector-flux  
**Trigger Word:** `v3ct0r`  
**Recommended Strength:** 0.6-0.9

#### Game Icon v1.0
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "game_icon_v1.safetensors"
```
**CivitAI Link:** https://civitai.com/models/31827/game-icon  
**Compatible:** SD 1.5  
**Recommended Strength:** 0.6-1.0

### 2. Pixel Art LoRAs

#### Retro Game Art (SDXL)
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "retro_game_art_sdxl.safetensors"
```
**CivitAI Link:** https://civitai.com/models/553027/sdxl-lora-retro-game-art  
**Trigger Word:** `r3tr0`  
**Recommended Strength:** 0.7-1.0

#### Retro Game Art (SD 1.5)
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "retro_game_art_sd15.safetensors"
```
**CivitAI Link:** https://civitai.com/models/550675/sd-15-lora-retro-game-art  
**Trigger Word:** `r3tr0`  
**Recommended Strength:** 0.7-1.0

### 3. Naval & Battleship LoRAs

#### Battleships v1.0
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "battleships_v1.safetensors"
```
**CivitAI Link:** https://civitai.com/models/110237/battleships  
**Trigger Word:** `battleship`  
**Resolution:** Best at 768x768  
**Recommended Strength:** 0.8-1.0

#### USS Iowa Battleship
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "uss_iowa_battleship.safetensors"
```
**CivitAI Link:** https://civitai.com/models/234609/uss-iowa-battleship  
**Trigger Word:** `iowa, battleship`  
**Recommended Strength:** 0.85-1.0

#### HMS Warspite Battleship
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "hms_warspite.safetensors"
```
**CivitAI Link:** https://civitai.com/models/224879/hms-warspite-battleship  
**Trigger Word:** `warspite`  
**Style:** Works best with "oil painting" in prompt  
**Recommended Strength:** 0.8-0.9

### 4. VFX & Explosion LoRAs

#### Explosion Matrix v2.0
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "explosion_matrix_v2.safetensors"
```
**CivitAI Link:** https://civitai.com/models/1069206/explosion-matrix  
**Trigger Word:** `exploder`  
**Secondary Triggers:** explosion, fire, lava, fireball, smoke, glowing  
**Clip Skip:** 1-2  
**Recommended Strength:** 0.6-1.0

#### FireVFX v2
```bash
curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o "firevfx_v2.safetensors"
```
**CivitAI Link:** https://civitai.com/models/9049/firevfx-create-more-consistent-fire  
**Trigger Words:** `pyrokinesis`, `fire magic`, `fireball`  
**Recommended Strength:** 0.6-1.0

## Restart ComfyUI

After downloading all LoRAs, restart ComfyUI:

```bash
# From magneto or SSH to moira
python C:\Users\jrjen\comfy-gen\scripts\restart_comfyui.py
```

## Verification

Verify LoRAs appear in ComfyUI API:

```bash
# From magneto
curl -s http://192.168.1.215:8188/object_info | python3 -c "
import json, sys
data = json.load(sys.stdin)
loras = data.get('LoraLoader', {}).get('input', {}).get('required', {}).get('lora_name', [[]])[0]
print('Available LoRAs:')
for lora in loras:
    print(f'  - {lora}')
"
```

## Testing Procedure

### Test 1: Battleship Icon (Top-Down)

**Goal:** Generate a clean battleship icon suitable for a game board.

**Command:**
```bash
python3 generate.py \
    --workflow workflows/game-icon-transparent.json \
    --prompt "(single battleship:1.8), top-down view, orthographic, no perspective, flat like a blueprint, military naval vessel, aircraft carrier, clean icon style, game asset, centered composition, white background, flat design, vector style, solid colors, simple shapes" \
    --negative-prompt "multiple ships, side view, perspective view, realistic photo, blurry, complex background, water, waves, ocean, scenery, text, watermark, 3D rendering, shadows" \
    --steps 80 \
    --cfg 8.5 \
    --lora "battleships_v1.safetensors:0.9" \
    --output /tmp/battleship_icon_test.png
```

**Expected Result:**
- Clean, top-down view of battleship
- White/blank background
- Centered composition
- Suitable for use as game icon

**Validation:**
1. Check if view is truly top-down (no perspective)
2. Verify single ship (not multiple)
3. Check background is clean/white
4. Assess if suitable for game use

### Test 2: Explosion Effect Sprite

**Goal:** Generate a cartoon-style explosion effect for hit animations.

**Command:**
```bash
python3 generate.py \
    --workflow workflows/game-icon-transparent.json \
    --prompt "(single explosion:1.8), game effect sprite, clean edges, cartoon explosion, orange and red flames, comic book style, centered, white background, bold outlines, simple shapes, vibrant colors" \
    --negative-prompt "realistic photo, multiple explosions, complex scene, background scenery, smoke clouds, text, watermark, blurry, detailed fire" \
    --steps 50 \
    --cfg 8.0 \
    --lora "explosion_matrix_v2.safetensors:0.8" \
    --output /tmp/explosion_sprite_test.png
```

**Expected Result:**
- Clean cartoon explosion
- Orange/red color scheme
- White background
- Suitable as sprite overlay

**Validation:**
1. Check if explosion is centered
2. Verify clean edges (not blurry)
3. Check if background is white/clean
4. Assess cartoon style quality

### Test 3: Pixel Art Ship Icon

**Goal:** Generate a retro-style pixel art ship.

**Command:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "r3tr0, pixel art battleship, 16-bit style, retro game sprite, top-down view, simple colors, 8-bit aesthetic, NES style" \
    --negative-prompt "realistic, photorealistic, 3D, modern graphics, complex details, gradients" \
    --steps 40 \
    --cfg 7.5 \
    --lora "retro_game_art_sd15.safetensors:0.9" \
    --output /tmp/pixel_battleship_test.png
```

**Expected Result:**
- Pixelated, retro style
- Low color depth
- Top-down view
- 8-bit/16-bit aesthetic

**Validation:**
1. Check for proper pixelation
2. Verify retro aesthetic
3. Assess color palette (limited colors)
4. Check if usable as game sprite

### Test 4: Vector Style Game Icon

**Goal:** Generate a clean vector-style icon with Flux.

**Command:**
```bash
python3 generate.py \
    --workflow workflows/game-icon-transparent.json \
    --prompt "v3ct0r, naval vessel icon, battleship, flat design, vector art, clean lines, simple shapes, game UI element, centered, white background, minimalist" \
    --negative-prompt "complex details, realistic photo, 3D, shadows, gradients, text, watermark" \
    --steps 40 \
    --cfg 8.0 \
    --lora "simple_vector_flux.safetensors:0.7" \
    --output /tmp/vector_icon_test.png
```

**Expected Result:**
- Clean vector-style artwork
- Simple, flat design
- White background
- Minimal details

**Validation:**
1. Check for vector aesthetic (flat, clean)
2. Verify trigger word worked
3. Assess if suitable for UI element
4. Check background cleanliness

### Test 5: Fire VFX Effect

**Goal:** Generate consistent fire effect for game VFX.

**Command:**
```bash
python3 generate.py \
    --workflow workflows/game-icon-transparent.json \
    --prompt "fireball, fire magic effect, game VFX sprite, glowing flames, magical fire, centered, white background, clean edges, vibrant orange and yellow" \
    --negative-prompt "realistic photo, complex background, smoke, multiple fireballs, text, watermark, blurry" \
    --steps 40 \
    --cfg 7.5 \
    --lora "firevfx_v2.safetensors:0.8" \
    --output /tmp/fire_vfx_test.png
```

**Expected Result:**
- Consistent fire effect
- Clean, game-ready sprite
- White background
- Suitable for VFX overlay

**Validation:**
1. Check fire consistency
2. Verify clean edges
3. Assess if usable as overlay
4. Check background

## LayerDiffusion Transparency Testing

**Note:** LayerDiffusion requires installation as a ComfyUI extension.

### Install LayerDiffusion (Optional - For True Transparency)

```bash
# SSH to moira
cd C:\Users\jrjen\AppData\Local\Programs\@comfyorgcomfyui-electron\resources\ComfyUI\custom_nodes

# Clone LayerDiffusion extension
git clone https://github.com/layerdiffusion/sd-forge-layerdiffuse

# Restart ComfyUI
python C:\Users\jrjen\comfy-gen\scripts\restart_comfyui.py
```

### Test True Transparency

After installing LayerDiffusion, modify the workflow to use the LayerDiffusion nodes for true alpha channel output. This requires updating the workflow JSON to include LayerDiffusion-specific nodes.

**Documentation:** https://github.com/layerdiffusion/sd-forge-layerdiffuse

## Post-Testing Tasks

### Update lora_catalog.yaml

After testing, update `lora_catalog.yaml`:

1. Remove `NOT_INSTALLED_` prefix from tested LoRAs
2. Update `recommended_strength` based on test results
3. Add any discovered trigger words or settings
4. Update `compatible_with` with confirmed checkpoint compatibility

### Update MODEL_REGISTRY.md

1. Move tested LoRAs from "Recommended Downloads" to main tables
2. Add file sizes
3. Add performance notes (generation time, VRAM usage)
4. Document any issues or special requirements

### Document Test Results

Create a summary document with:
- Generation quality assessment (1-10 scale)
- Optimal settings found during testing
- Any issues or limitations discovered
- Recommendations for use cases
- Sample images uploaded to MinIO

## Viewing Generated Images

All test images will be available at:
```
http://192.168.1.215:9000/comfy-gen/<timestamp>_<filename>.png
```

To list all generated images:
```bash
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+'
```

## Troubleshooting

### LoRA Not Found
- Verify file is in `C:\Users\jrjen\comfy\models\loras\`
- Restart ComfyUI
- Check filename matches exactly (case-sensitive)

### Poor Quality Output
- Increase steps (try 60-100)
- Adjust CFG (try 7.5-9.0)
- Modify LoRA strength (+/- 0.2)
- Refine prompt with more constraints

### Wrong View/Perspective
- Add stronger emphasis: "(top-down view:2.0)"
- Add negative prompts: "side view, perspective, 3D, angled"
- Use "orthographic" and "blueprint" keywords
- Increase CFG for stronger prompt adherence

### Background Not Clean
- Add to negative prompt: "scenery, detailed background, landscape"
- Emphasize in prompt: "(white background:1.5), isolated object"
- Consider using background removal post-processing
- Or install LayerDiffusion for true transparency

## Success Criteria

Tests are successful when:
- [ ] All LoRAs load in ComfyUI API
- [ ] Battleship icons show true top-down view
- [ ] Explosions are clean and game-ready
- [ ] Pixel art has proper retro aesthetic
- [ ] Vector icons are flat and clean
- [ ] Fire effects are consistent
- [ ] Backgrounds are clean (white or transparent)
- [ ] All outputs are suitable for game use

## Next Steps After Testing

1. Update documentation with test results
2. Create presets in `presets.yaml` for common scenarios
3. Add tested LoRAs to MCP server tools
4. Generate sample asset library for reference
5. Document any workflow modifications needed
6. Consider training custom LoRAs for project-specific needs
