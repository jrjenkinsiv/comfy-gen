# Battleship Game Sprite Generation Guide

This guide documents the process for generating battleship game sprites using ComfyGen.

## Requirements

- **Resolution**: 48x48px per ship section (will generate at 512x512 and resize)
- **Perspective**: Top-down orthographic view
- **Style**: Game-ready sprites, clear silhouettes
- **Format**: PNG with transparency support
- **Ship Structure**: Each ship divided into sections (1/4, 1/3, 1/5 depending on ship size)

## Ship Section Anatomy

For a battleship (typically 4-5 sections):
- **Bow (Front)**: Pointed front section with gun turrets
- **Mid-Front**: Main superstructure, bridge, smokestacks
- **Mid-Rear**: Additional turrets, secondary structures
- **Stern (Back)**: Rear turrets, helipad/fantail

## Prompt Structure for Battleship Sections

### Base Prompt Template
```
battleship section, naval warship, top-down view, orthographic projection, 
game sprite, pixel art style, clear silhouette, military gray hull,
{SECTION_DETAILS}, {STYLE_MODIFIERS}
```

### Section-Specific Details

**Bow Section (1/4):**
```
front bow section, pointed prow, forward gun turret, anchor chains,
deck plating, bow wave foam
```

**Mid-Front Section (2/4):**
```
superstructure, command bridge, radar arrays, smokestacks, 
communication towers, observation deck
```

**Mid-Rear Section (3/4):**
```
mid-ship section, secondary gun turrets, deck equipment, 
cargo cranes, life boats
```

**Stern Section (4/4):**
```
rear stern section, aft gun turrets, helipad markings,
flagpole, rear deck equipment
```

### Style Modifiers

**Modern Warship:**
```
modern naval destroyer, stealth design, angular surfaces, 
phased array radar, missile launchers
```

**WWII Era:**
```
World War 2 battleship, classic design, large gun turrets,
rounded superstructure, vintage military aesthetic
```

**Pixel Art:**
```
16-bit pixel art, retro game graphics, dithered shading,
limited color palette, clean edges
```

**Realistic:**
```
photorealistic, detailed metal textures, rust and weathering,
deck equipment detail, rivets and panels
```

## Negative Prompts

Critical negatives to avoid common issues:

```
side view, perspective angle, 3D render, isometric, diagonal view,
people, characters, water, ocean waves, multiple ships, text, UI,
blurry, low quality, distorted proportions, asymmetrical
```

## Generation Workflow

### Step 1: Generate at Higher Resolution
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "battleship bow section, top-down view, naval warship, game sprite..." \
    --negative-prompt "side view, perspective, 3D, people, water..." \
    --output /tmp/battleship_section.png
```

### Step 2: Resize to 48x48px
```bash
# Using ImageMagick
convert /tmp/battleship_section.png -resize 48x48! /tmp/battleship_48x48.png

# Using Python PIL (maintains aspect ratio)
python3 -c "from PIL import Image; img=Image.open('/tmp/battleship_section.png'); img.thumbnail((48,48)); img.save('/tmp/battleship_48x48.png')"
```

### Step 3: Add Transparency (if needed)
```bash
# Remove white background
convert /tmp/battleship_48x48.png -transparent white /tmp/battleship_final.png
```

## Example Prompts for 6 Variations

### Variation 1: Modern Bow Section
```
Prompt: battleship bow section, modern naval destroyer, top-down orthographic view, 
pointed prow, forward gun turret, stealth design, angular surfaces, military gray hull, 
deck plating, game sprite, clean silhouette, 16-bit pixel art style

Negative: side view, perspective angle, 3D render, people, water, ocean, multiple ships, 
blurry, distorted proportions
```

### Variation 2: WWII Bow Section (Weathered)
```
Prompt: battleship bow section, World War 2 battleship, top-down view, vintage warship, 
pointed bow, large forward gun turret, weathered metal, rust streaks, battle damage, 
deck equipment, classic design, game sprite, detailed pixel art

Negative: modern design, clean surfaces, side view, perspective, 3D, people, water, 
text, low quality
```

### Variation 3: Cartoon/Stylized Bow
```
Prompt: battleship bow section, top-down view, cartoon style, stylized naval ship, 
bright colors, bold outlines, simplified design, game sprite, mobile game aesthetic, 
cute military ship, exaggerated proportions

Negative: realistic, photorealistic, gritty, dark, side view, perspective, people, 
water, complex details
```

### Variation 4: Pixel Art (Retro Style)
```
Prompt: battleship bow section, top-down view, 8-bit pixel art, retro game graphics, 
NES style, limited color palette, dithered shading, simple geometric shapes, 
classic naval ship, game sprite

Negative: high resolution, detailed, photorealistic, smooth gradients, side view, 
3D, people, water
```

### Variation 5: Detailed Realistic Bow
```
Prompt: battleship bow section, top-down orthographic view, photorealistic, 
detailed metal textures, rivets and panels, deck equipment, anchor chains, 
forward turret with dual cannons, military gray paint, anti-rust coating, 
game sprite, high detail

Negative: side view, perspective, cartoon, simplified, people, characters, water, 
ocean, blurry, low quality
```

### Variation 6: Damaged/Battle-Worn Bow
```
Prompt: battleship bow section, top-down view, battle-damaged warship, 
burn marks, shell impacts, dented hull plating, exposed metal, rust patches, 
forward turret damaged, realistic weathering, military gray with damage, game sprite

Negative: pristine, clean, new, side view, perspective, people, water, multiple ships, 
cartoon style, low quality
```

## Post-Processing Checklist

- [ ] Image is top-down orthographic view
- [ ] Silhouette is clear and recognizable
- [ ] Colors are appropriate for game (not too dark/light)
- [ ] Edges are clean (no anti-aliasing artifacts if pixel art)
- [ ] Size is exactly 48x48px
- [ ] Transparency is applied if needed
- [ ] Image works on both light and dark backgrounds

## Future Ship Types

### Destroyer (3 sections)
- Smaller, faster ship
- Sleek profile
- Fewer gun turrets

### Submarine (2-3 sections)
- Narrow profile
- Conning tower visible
- Periscope mast

### Aircraft Carrier (5 sections)
- Wide flight deck
- Island superstructure on one side
- Deck markings for aircraft

### Cruiser (4 sections)
- Medium size
- Balanced armament
- Streamlined design

## Tips for Consistency

1. **Use same base negative prompts** across all variations
2. **Maintain consistent lighting** (overhead, no shadows)
3. **Use same color palette** for ship class
4. **Keep scale consistent** across ship sections
5. **Test against game background** before finalizing
6. **Generate multiple attempts** and cherry-pick best results

## Storage Organization

```
/battleship/sprites/
  ├── battleship/
  │   ├── bow_modern.png
  │   ├── bow_wwii.png
  │   ├── bow_damaged.png
  │   ├── mid1_modern.png
  │   └── ...
  ├── destroyer/
  ├── cruiser/
  └── carrier/
```

## Integration with Battleship Game

After generation, sprites should be:
1. Resized to 48x48px
2. Exported with transparency
3. Named with consistent convention: `{ship_type}_{section}_{variant}.png`
4. Tested in game engine for visual clarity
5. Adjusted for contrast if needed

## Validation Workflow

Before using in production:
- Generate at multiple sizes (48x48, 64x64, 96x96) to test scalability
- Use `--validate --auto-retry` if quality is inconsistent
- Check against both light/dark game backgrounds
- Verify ship sections align properly when placed adjacent
