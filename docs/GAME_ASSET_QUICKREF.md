# Game Asset LoRA Research - Quick Reference

This is a quick reference guide for the game asset LoRA research completed in this PR.

## What Was Completed

### ✅ Research (All Categories)
- **Game Icons:** 4 models (Flux & SD 1.5)
- **Pixel Art:** 6 models (SDXL & SD 1.5)
- **Naval/Battleships:** 6 models (all SD 1.5)
- **VFX/Explosions:** 4 models (SDXL & SD 1.5)
- **Sprite Sheets:** 3 workflows/models
- **Transparency:** LayerDiffusion technique researched

### ✅ Documentation Created
1. **MODEL_REGISTRY.md** - Game Assets section with 25+ models
2. **lora_catalog.yaml** - 10 LoRA entries + keyword mappings
3. **workflows/game-icon-transparent.json** - New workflow
4. **GAME_ASSET_TESTING.md** - Complete testing guide
5. **USAGE.md** - Game Asset Generation section

## Top 3 Recommendations Per Category

### Icons & Flat Design
1. **Flux LoRA - Flat Art Style** (Flux) - Best quality
2. **Simple Vector Flux** (Flux) - Trigger: `v3ct0r`
3. **Game Icon v1.0** (SD 1.5) - SD 1.5 option

### Naval/Battleships
1. **Battleships v1.0** (SD 1.5) - General purpose
2. **USS Iowa** (SD 1.5) - Realistic Iowa-class
3. **HMS Warspite** (SD 1.5) - Oil painting style

### VFX/Explosions
1. **Explosion Matrix v2** (SDXL) - ⚠️ Requires SDXL checkpoint
2. **FireVFX v2** (SD 1.5) - Consistent fire effects
3. **Explosive AnimateDiff** (SD 1.5) - Motion-based

### Pixel Art
1. **Retro Game Art SDXL** (SDXL) - ⚠️ Requires SDXL checkpoint
2. **Retro Game Art SD15** (SD 1.5) - Same quality, SD 1.5
3. **2D Pixel Toolkit** (SD 1.5) - True pixel art

### Sprite Sheets
1. **Sprite Sheet Maker** - Complete workflow
2. **SDXL LoRA Slider** (SDXL) - ⚠️ Requires SDXL
3. **Dynamic Poses** (SDXL) - ⚠️ Requires SDXL

## ⚠️ Important Notes

### SDXL Requirements
Several models require an SDXL checkpoint:
- Explosion Matrix v2
- Retro Game Art (SDXL version)
- Sprite Sheet LoRAs

**If you don't have SDXL:** Use the SD 1.5 alternatives listed

### Current Checkpoints Available
According to MODEL_REGISTRY.md:
- ✅ SD 1.5: `v1-5-pruned-emaonly-fp16.safetensors`
- ✅ Flux.1 Dev: `flux1-dev-fp8.safetensors` (if available)
- ❌ SDXL: **NOT CURRENTLY INSTALLED**

**Action Required:** Download SDXL checkpoint if testing SDXL LoRAs

## Testing Priority Order

### Phase 1: SD 1.5 Models (No New Checkpoint Needed)
1. Game Icon v1.0
2. Battleships v1.0
3. USS Iowa or HMS Warspite
4. FireVFX v2
5. Retro Game Art (SD 1.5)

### Phase 2: Flux Models (If Flux Checkpoint Available)
1. Flux Flat Art Style
2. Simple Vector Flux

### Phase 3: SDXL Models (Requires SDXL Download)
1. Download SDXL checkpoint first
2. Retro Game Art (SDXL)
3. Explosion Matrix v2
4. SDXL LoRA Slider

## Quick Test Commands

### Test 1: Battleship Icon (SD 1.5)
```bash
python3 generate.py \
    --workflow workflows/game-icon-transparent.json \
    --prompt "(single battleship:1.8), top-down view, orthographic, military vessel, clean icon style, game asset, centered, white background, flat design" \
    --negative-prompt "multiple ships, side view, perspective, realistic photo, complex background, water, scenery, text" \
    --steps 80 --cfg 8.5 \
    --output ./output/battleship_test.png
```

### Test 2: Explosion Sprite (SD 1.5)
```bash
python3 generate.py \
    --workflow workflows/game-icon-transparent.json \
    --prompt "(single explosion:1.8), game effect sprite, clean edges, cartoon explosion, orange and red, comic book style, centered, white background" \
    --negative-prompt "realistic photo, multiple explosions, complex scene, background scenery, text" \
    --steps 50 --cfg 8.0 \
    --output ./output/explosion_test.png
```

### Test 3: Pixel Art (SD 1.5)
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "r3tr0, pixel art battleship, 16-bit style, retro game sprite, top-down view, simple colors, NES style" \
    --negative-prompt "realistic, photorealistic, 3D, modern graphics, complex details" \
    --steps 40 --cfg 7.5 \
    --output ./output/pixel_ship_test.png
```

## After Testing

### Update lora_catalog.yaml
1. Remove `NOT_INSTALLED_` prefix
2. Update `compatible_with` with actual checkpoint used
3. Update `recommended_strength` based on tests
4. Add any notes about quality or issues

### Update MODEL_REGISTRY.md
1. Move tested models to main tables
2. Add file sizes
3. Add performance notes
4. Document any issues

## Resources

- **Full Testing Guide:** `docs/GAME_ASSET_TESTING.md`
- **Usage Examples:** `docs/USAGE.md` - Game Asset Generation section
- **Model Registry:** `docs/MODEL_REGISTRY.md` - Game Assets section
- **LoRA Catalog:** `lora_catalog.yaml` - Search for "NOT_INSTALLED"

## CivitAI Download Links

All CivitAI links are in MODEL_REGISTRY.md under each category.

**To find version IDs:**
1. Visit the CivitAI link
2. Click on desired version
3. Copy version ID from URL or download button
4. Use: `curl -L "https://civitai.com/api/download/models/[VERSION_ID]" -o filename.safetensors`

## Questions?

See the comprehensive guides:
- **GAME_ASSET_TESTING.md** - Complete testing procedure
- **USAGE.md** - Usage examples and troubleshooting
- **MODEL_REGISTRY.md** - All model details and compatibility

## Success Criteria

Testing is successful when:
- [ ] All downloaded LoRAs load in ComfyUI
- [ ] Battleship icons show true top-down view
- [ ] Explosions are clean and game-ready
- [ ] Pixel art has proper retro aesthetic
- [ ] Backgrounds are clean (white or transparent)
- [ ] All outputs suitable for game use
- [ ] Documentation updated with test results
