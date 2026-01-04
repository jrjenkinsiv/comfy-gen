# Detailed Prompting Guide for Image Generation

## Overview

Stable Diffusion and similar models can handle **paragraph-length prompts** with extensive detail. Longer, more descriptive prompts produce more precise results by narrowing the sampling space and reducing ambiguity.

## Key Principles

### 1. **Be Specific, Not Brief**

❌ **Bad:** "battleship bow section, top-down view"

✅ **Good:** "A battleship bow section sprite for a board game, viewed from directly overhead as if looking straight down from a satellite or helicopter hovering perfectly level above the ship. The perspective must be completely flat with zero angle, zero depth, and zero perspective distortion - imagine an architectural floor plan or a piece from a classic naval strategy board game like Battleship."

### 2. **Layer Your Constraints**

Good prompts build constraints in layers:

1. **Subject** - What is the main subject?
2. **Perspective/View** - Viewing angle, camera position
3. **Style** - Art style, medium, technique
4. **Details** - Specific elements, textures, materials
5. **Constraints** - What to avoid, what must be present
6. **Technical specs** - Lighting, color palette, composition

### 3. **Use Redundant Reinforcement**

Repeat critical concepts with different phrasing:

"The view should be purely orthographic, as flat as paper, with no vanishing points, no horizon line, and no foreshortening whatsoever."

This tells the model THREE ways that the perspective must be flat.

### 4. **Provide Visual Anchors**

Reference familiar objects or concepts:

"Think board game component, military strategy map marker, or naval architecture blueprint"

This gives the model concrete visual references to guide generation.

## Anatomy of a Detailed Prompt

### Structure Template

```
[SUBJECT DESCRIPTION]
[PERSPECTIVE/VIEW DETAILS]
[STYLE AND MEDIUM]
[SPECIFIC ELEMENTS]
[CONSTRAINTS AND EXCLUSIONS]
[TECHNICAL SPECIFICATIONS]
[MOOD AND ATMOSPHERE]
```

### Example: Battleship Sprite

```
A battleship bow section sprite for a board game, viewed from directly overhead as if looking straight down from a satellite or helicopter hovering perfectly level above the ship. 

The perspective must be completely flat with zero angle, zero depth, and zero perspective distortion - imagine an architectural floor plan or a piece from a classic naval strategy board game like Battleship. 

The view should be purely orthographic, as flat as paper, with no vanishing points, no horizon line, and no foreshortening whatsoever. 

The ship section shows the forward bow with pointed prow, a single gun turret with dual cannons, deck plating with riveted panels, anchor equipment, and military gray paint. 

The image must look like it could be a game token that players would place on a grid, with clean edges and a simple silhouette that reads clearly from above. 

Think board game component, military strategy map marker, or naval architecture blueprint - absolutely no side angle, no diagonal view, no isometric projection.
```

## Keyword Categories

Based on research from stable-diffusion-art.com, effective prompts include:

### 1. **Subject**
- Who/what is the main focus?
- What are they doing?
- What do they look like?

**Example:** "a powerful mysterious sorceress, sitting on a rock, casting lightning magic, wearing detailed leather clothing with gemstones and a hat"

### 2. **Medium**
- Material/technique: "digital art", "oil painting", "3D render", "photography"
- Strong effect on overall style

### 3. **Style**
- Artistic movement: "hyperrealistic", "impressionist", "cyberpunk"
- Artist names: "by Greg Rutkowski", "by Makoto Shinkai"

### 4. **Resolution/Quality**
- "highly detailed", "sharp focus", "8K", "intricate"
- "masterpiece", "best quality"

### 5. **Color**
- Overall palette: "iridescent gold", "vibrant colors", "muted tones"
- Specific colors: "blue eyes", "white dress"

### 6. **Lighting**
- "studio lighting", "volumetric lighting", "soft shadows"
- "cinematic lighting", "rim lighting", "ambient light"

### 7. **Composition**
- "centered", "wide angle", "close-up", "full body"
- "rule of thirds", "symmetrical"

### 8. **Additional Details**
- Atmosphere: "dystopian", "ethereal", "magical"
- Texture: "smooth", "rough", "glossy"

## Negative Prompts

Just as important as positive prompts. Be explicit about what to avoid:

**Universal negative prompt:**
```
disfigured, deformed, ugly, bad anatomy, bad proportions, blurry, low quality, 
lowres, jpeg artifacts, watermark, text, signature
```

**Perspective-specific negatives:**
```
perspective, side view, diagonal, isometric, 3D, angled, tilted, depth, 
foreshortening, vanishing point, horizon line
```

## Prompt Length Guidelines

- **Minimum effective:** 50-75 tokens (basic description)
- **Recommended:** 100-200 tokens (detailed paragraph)
- **Maximum useful:** 300+ tokens (highly specific, complex scenes)

Stable Diffusion processes prompts in 75-token chunks. Use the keyword `BREAK` to start a new chunk if grouping related concepts.

## Keyword Weighting

Increase importance of critical keywords:

**Syntax:** `(keyword:1.5)` or `((keyword))` (each pair of parentheses = 1.1x weight)

**Example:**
```
(orthographic view:1.5), (flat perspective:1.4), (top-down:1.3), no 3D depth
```

Decrease importance:

**Syntax:** `(keyword:0.7)` or `[[keyword]]` (each pair of brackets = 0.9x weight)

## Common Mistakes to Avoid

❌ **Too vague:** "a ship" (which ship? what angle? what style?)

❌ **Conflicting directions:** "realistic fantasy" (pick one tone)

❌ **Assuming knowledge:** "like the one in the movie" (model doesn't know)

❌ **Overloading style keywords:** Using 10 artist names creates chaos

✅ **Specific and detailed:** "A modern destroyer viewed from directly above..."

✅ **Consistent tone:** "photorealistic military equipment, studio lighting..."

✅ **Clear references:** "architectural blueprint style, orthographic projection..."

## Step-by-Step Prompting Process

### 1. **Start Simple, Iterate**

Generate 4-6 images with a basic prompt, assess results.

### 2. **Add Detail Incrementally**

Add 1-2 new constraint categories at a time.

### 3. **Use Validation Strategically**

- CLIP validation checks semantic match, not visual quality
- Use `--positive-threshold 0.85` for stricter matching
- Increase steps (`--steps 80`) for complex prompts

### 4. **Refine Based on Results**

- If perspective is wrong → strengthen view keywords, add to negative prompt
- If style is off → adjust artist references, medium keywords
- If details are missing → add specific element descriptions

## Examples by Use Case

### Character Portrait

```
A beautiful sorceress with long flowing hair and piercing blue eyes, wearing 
ornate leather armor decorated with glowing gemstones, sitting confidently on 
an ancient stone throne inside a gothic castle. Digital art in the style of 
Greg Rutkowski and Artgerm, hyperrealistic rendering with dramatic volumetric 
lighting streaming through tall arched windows, cinematic composition, highly 
detailed textures on clothing and jewelry, sharp focus on facial features, 
8K resolution, trending on ArtStation.

Negative: ugly, deformed, blurry, cartoon, anime, low quality, bad anatomy
```

### Architectural Scene

```
A Persian temple interior with soaring vaulted ceilings and intricate 
geometric tilework in turquoise and gold, filled with hanging gardens 
overflowing with roses and jasmine, soft volumetric light filtering through 
ornate lattice windows creating dappled shadows on marble floors. 
Architectural photography in the style of Isfahan's historic mosques, 
photorealistic rendering with careful attention to Islamic geometric patterns, 
soft color palette of ivory, rose pink, and aquamarine, slight atmospheric 
mist adding depth, wide-angle composition showing the full height of the 
atrium, 8K detail, trending on Behance.

Negative: modern, minimalist, dark, gloomy, oversaturated
```

### Game Asset (Sprite)

```
A medieval castle tower piece for a board game, viewed from directly overhead 
as if looking straight down from a bird's eye perspective. The view must be 
purely orthographic with absolutely no angle, no perspective distortion, and 
no depth - imagine an architectural floor plan or a game token from classic 
strategy board games like Catan or Risk. The tower shows a circular stone 
structure with crenellated battlements, a conical red roof with ceramic tiles, 
small window openings, and weathered gray stone texture. The image must look 
like a flat game piece that players would place on a hex grid, with clean 
edges and a simple silhouette that reads clearly from above. Think board game 
component, strategy game map marker, or architectural blueprint - absolutely 
no side view, no diagonal angle, no isometric projection, no 3D rendering.

Negative: perspective, isometric, 3D, side view, angled, diagonal, depth, 
shadows, foreshortening, vanishing point, horizon, realistic lighting
```

## Best Practices for Agents

When generating images programmatically:

1. **Default to verbose prompts** - More detail = better results
2. **Include negative prompts** - Always specify what to avoid
3. **Use appropriate steps** - 30 for drafts, 80+ for final output
4. **Adjust CFG scale** - 7.0 default, 8-10 for stronger prompt adherence
5. **Set validation thresholds** - 0.85-0.95 for quality checks

## Resources

- [Stable Diffusion Art Prompt Guide](https://stable-diffusion-art.com/prompt-guide/)
- [PromptHero Examples](https://prompthero.com/stable-diffusion-prompts)
- Model-specific guidance in `/docs/AGENT_GUIDE.md`

---

**Remember:** The model can't read your mind. Say exactly what you want in as much detail as needed. More words = more control.
