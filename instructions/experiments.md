# ComfyGen Experiments & Batch Generation

**Last updated:** 2026-01-07

This guide explains how to run experiments and batch generations in comfy-gen. Use these procedures when the user asks to "run an experiment", "generate variations", "test different options", or "batch generate".

---

## Table of Contents

1. [Quick Reference](#quick-reference-what-the-agent-must-know)
2. [Types of Experiments](#types-of-experiments)
3. [Batch Script Template](#batch-script-template)
4. [Project & Tagging System](#project--tagging-system)
5. [Output Standards](#output-standards)
6. [Gallery Organization](#gallery-organization)
7. [Consuming Results](#consuming-results)
8. [Workflow Selection](#workflow-selection-guide)
9. [Common Negative Prompts](#common-negative-prompts-by-category)
10. [Troubleshooting](#troubleshooting)

---

## Quick Reference: What the Agent Must Know

### When User Says "Run an experiment" or "Generate variations"

**The agent MUST:**
1. Ask for (or infer from context):
   - **Subject**: What are we generating? (character, scene, object, etc.)
   - **Variations**: What should vary? (poses, expressions, LoRAs, styles, etc.)
   - **Count**: How many variations? (default: 50)
   - **Project**: What project is this for? (e.g., "youngboh", "nsfw-test", etc.)
   
2. Create a batch script with:
   - Project tag in all filenames
   - Variation arrays for each parameter
   - Nested loops to generate combinations
   - Results saved to JSON with full metadata
   - All image URLs extracted and returned
   
3. **ALWAYS return all generated image URLs directly** - never say "check the bucket" or give patterns

4. **ALWAYS provide a consumption summary** with:
   - Gallery link with project filter
   - Top-scoring images highlighted
   - Quick visual comparison recommendations

### Minimum Information Needed

| Parameter | Required? | Default |
|-----------|-----------|---------|
| Subject/character description | YES | - |
| What to vary | YES | - |
| Project name | NO | infer from context or use "experiment" |
| Workflow | NO | infer from subject type |
| Count | NO | 50 |
| Negative prompt | NO | standard for category |

---

## Types of Experiments

### 1. Character Variation Batch

Generate multiple variations of a character to pick the best design.

**User provides:**
- Character description (appearance, clothing, style)
- What to vary: poses, expressions, angles, LoRAs

**Example request:** "Generate 50 variations of youngboh character with different poses and expressions"

**Standard variations to test:**
```python
POSES = [
    "standing straight, arms at sides, neutral stance",
    "standing with hands in pockets, casual stance",
    "walking forward, mid-step",
    "leaning against wall, relaxed pose",
    "sitting on chair, legs crossed",
    "standing with arms crossed, defensive posture",
    "running pose, action shot",
    "crouching down, dynamic pose",
]

EXPRESSIONS = [
    "neutral calm expression",
    "happy smiling face",
    "sad disappointed look",
    "angry determined expression",
    "nervous awkward expression",
    "confident smirk",
    "worried anxious face",
    "surprised shocked expression",
]

ANGLES = [
    "front view, facing camera directly",
    "3/4 view, slightly angled",
    "side profile view",
]
```

### 2. Style/LoRA Comparison

Test different style LoRAs on the same subject.

**User provides:**
- Base subject description
- LoRAs to compare (or "test available LoRAs")

**Standard approach:**
```python
LORAS = [
    None,  # Baseline without LoRA
    "LoRA_A.safetensors:0.5",
    "LoRA_A.safetensors:0.7",
    "LoRA_B.safetensors:0.5",
]
```

### 3. Parameter Space Exploration

Test different sampling parameters.

**Standard parameter space:**
```python
SAMPLERS = ["euler", "euler_ancestral", "dpmpp_2m_sde", "dpmpp_2m"]
CFG_VALUES = [5.0, 6.0, 7.0, 7.5, 8.0]
STEP_VALUES = [30, 40, 50, 70]
SCHEDULERS = ["normal", "karras"]
```

### 4. Scene/Subject Batch

Generate multiple subjects or scenes.

**User provides:**
- List of subjects/scenes to generate
- Common style/parameters

---

## Batch Script Template

When creating a batch generation script, use this template:

```python
#!/usr/bin/env python3
"""
Batch generation for [PROJECT/PURPOSE].
[DESCRIPTION OF WHAT THIS TESTS]
"""

import json
import subprocess
import sys
from pathlib import Path

# Paths
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"
OUTPUT_DIR = Path("/tmp/[project]_batch")
OUTPUT_DIR.mkdir(exist_ok=True)

# Base description
BASE_SUBJECT = "[DETAILED SUBJECT DESCRIPTION]"

# Variations to test
VARIATIONS_A = [
    "variation 1",
    "variation 2",
    # ...
]

VARIATIONS_B = [
    "variation 1",
    "variation 2",
    # ...
]

LORAS = [
    None,  # Baseline
    "lora_name.safetensors:0.5",
]

# Standard negative prompt
NEGATIVE_PROMPT = "[APPROPRIATE NEGATIVE PROMPT FOR CATEGORY]"

def generate_variations():
    """Generate a grid of variations."""
    
    results = []
    test_id = 1
    target_count = 50  # Adjust as needed
    
    for var_a in VARIATIONS_A:
        for var_b in VARIATIONS_B:
            for lora in LORAS:
                if test_id > target_count:
                    break
                    
                # Build prompt
                prompt = f"{BASE_SUBJECT}, {var_a}, {var_b}, [STYLE TAGS]"
                
                # Build command
                output_file = OUTPUT_DIR / f"batch_{test_id:03d}.png"
                
                cmd = [
                    sys.executable, str(GENERATE_PY),
                    "--workflow", "workflows/[WORKFLOW].json",
                    "--prompt", prompt,
                    "--negative-prompt", NEGATIVE_PROMPT,
                    "--steps", "40",
                    "--cfg", "7.5",
                    "--project", "[PROJECT_NAME]",  # For gallery filtering
                    "--tags", f"batch:1,var_a:{var_a.split(',')[0]},var_b:{var_b.split(',')[0]}",
                    "--output", str(output_file),
                ]
                
                if lora:
                    cmd.extend(["--lora", lora])
                
                print(f"\n{'='*60}")
                print(f"[{test_id}/{target_count}] Generating...")
                print(f"Variation A: {var_a}")
                print(f"Variation B: {var_b}")
                print(f"LoRA: {lora or 'None'}")
                print(f"{'='*60}")
                
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=str(COMFY_GEN_DIR),
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    
                    # Extract image URL
                    image_url = None
                    for line in result.stdout.split('\n'):
                        if 'http://192.168.1.215:9000/comfy-gen/' in line:
                            parts = line.split('http://192.168.1.215:9000/comfy-gen/')
                            if len(parts) > 1:
                                filename = parts[1].strip().split()[0]
                                if filename.endswith('.png'):
                                    image_url = f"http://192.168.1.215:9000/comfy-gen/{filename}"
                                    break
                    
                    # Extract score
                    score = None
                    for line in result.stdout.split('\n'):
                        if 'Score:' in line:
                            try:
                                score = float(line.split('Score:')[1].strip())
                            except:
                                pass
                            break
                    
                    results.append({
                        "id": test_id,
                        "status": "success" if result.returncode == 0 else "failed",
                        "var_a": var_a,
                        "var_b": var_b,
                        "lora": lora,
                        "url": image_url,
                        "score": score,
                        "returncode": result.returncode,
                    })
                    
                    if image_url:
                        print(f"[OK] Generated: {image_url}")
                        print(f"[OK] Score: {score}")
                        
                except subprocess.TimeoutExpired:
                    print(f"[ERROR] Timeout")
                    results.append({"id": test_id, "status": "timeout", "var_a": var_a, "var_b": var_b})
                except Exception as e:
                    print(f"[ERROR] {e}")
                    results.append({"id": test_id, "status": "error", "error": str(e)})
                
                test_id += 1
            
            if test_id > target_count:
                break
        if test_id > target_count:
            break
    
    # Save results
    results_file = COMFY_GEN_DIR / "[project]_batch_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Batch complete! Results: {results_file}")
    print(f"Success: {len([r for r in results if r['status'] == 'success'])}/{len(results)}")
    print(f"{'='*60}")
    
    # Print all URLs
    print("\nAll generated images:")
    for r in results:
        if r['status'] == 'success' and r.get('url'):
            print(f"[{r['id']:03d}] {r['url']} (score: {r.get('score', 'N/A')})")

if __name__ == "__main__":
    generate_variations()
```

---

## Project & Tagging System

### Filename Convention (CRITICAL)

All batch-generated files MUST include the project name in the filename:

```
{timestamp}_{project}_{batch_id}.png
```

**Examples:**
- `20260107_100727_youngboh_001.png` - youngboh character batch
- `20260107_142315_nsfw_handjob_042.png` - NSFW experiment
- `20260107_093500_battleship_icons_015.png` - game assets

**Why this matters:**
- Gallery can filter by prefix (project name)
- Easy to find all images from an experiment
- Prevents mixing unrelated generations

### Project Tag in Batch Scripts

```python
# Set project name at top of script
PROJECT = "youngboh"  # or "nsfw", "battleship", etc.

# Use in output filename
output_file = OUTPUT_DIR / f"{PROJECT}_{test_id:03d}.png"

# Use in generate.py with --project flag
cmd = [
    sys.executable, str(GENERATE_PY),
    "--project", PROJECT,  # Stored in metadata for gallery filtering
    "--tags", "batch:1,pose:standing",  # Optional key:value tags
    # ...
    "--output", str(output_file),
]
```

### CLI Flags for Organization

| Flag | Purpose | Example |
|------|---------|---------|
| `--project` | Project name for gallery filtering | `--project youngboh` |
| `--tags` | Key:value metadata tags | `--tags "pose:standing,expression:happy"` |
| `--batch-id` | Batch run identifier | `--batch-id batch_001` |

These flags store organization data in the JSON metadata:
```json
{
  "organization": {
    "project": "youngboh",
    "batch_id": "batch_001",
    "tags": {"pose": "standing", "expression": "happy"}
  }
}
```
```bash
python3 generate.py \
    --workflow workflows/illustrious-anime.json \
    --prompt "..." \
    --tags "project:youngboh,batch:char-poses,character:protagonist" \
    --output /tmp/youngboh_001.png
```

Tags will be stored in the JSON metadata sidecar:
```json
{
  "tags": {
    "project": "youngboh",
    "batch": "char-poses",
    "character": "protagonist",
    "experiment_date": "2026-01-07"
  }
}
```

---

## Output Standards

### Standard Output Format

After batch generation, agent MUST provide:

#### 1. Summary Statistics
```
============================================================
Batch generation complete!
Project: youngboh
Total: 50 images
Success: 48/50 (96%)
Score range: 0.657 - 0.676
Top scorer: #042 (0.676)
============================================================
```

#### 2. ALL Image URLs (clickable)
```
All generated images:
http://192.168.1.215:9000/comfy-gen/20260107_100727_youngboh_001.png
http://192.168.1.215:9000/comfy-gen/20260107_100740_youngboh_002.png
... (EVERY single image)
```

#### 3. Gallery Quick Access
```
View in Gallery:
http://192.168.1.162:8080/?search=youngboh&sort=quality

Top 5 by score:
1. http://192.168.1.215:9000/comfy-gen/20260107_101526_youngboh_042.png (0.676)
2. http://192.168.1.215:9000/comfy-gen/20260107_101131_youngboh_022.png (0.673)
3. http://192.168.1.215:9000/comfy-gen/20260107_100750_youngboh_003.png (0.672)
4. http://192.168.1.215:9000/comfy-gen/20260107_101414_youngboh_036.png (0.672)
5. http://192.168.1.215:9000/comfy-gen/20260107_100911_youngboh_010.png (0.672)
```

#### 4. Results JSON Location
```
Full results with metadata: /Users/jrjenkinsiv/Development/comfy-gen/youngboh_batch_results.json
```

### Results JSON Structure

Save comprehensive metadata for each generation:

```json
{
  "project": "youngboh",
  "batch_id": "char-poses-20260107",
  "timestamp": "2026-01-07T10:07:27",
  "total_images": 50,
  "successful": 48,
  "failed": 2,
  "parameters": {
    "workflow": "illustrious-anime.json",
    "steps": 40,
    "cfg": 7.5,
    "base_prompt": "The Boondocks anime style..."
  },
  "results": [
    {
      "id": 1,
      "status": "success",
      "variations": {
        "pose": "standing straight",
        "expression": "nervous",
        "angle": "front view",
        "lora": null
      },
      "url": "http://192.168.1.215:9000/comfy-gen/20260107_100727_youngboh_001.png",
      "score": 0.66,
      "full_prompt": "The Boondocks anime style, ... standing straight, nervous..."
    }
  ]
}
```

---

## Gallery Organization

### Current Gallery Features

The gallery at `http://192.168.1.162:8080` supports:

| Feature | How to Use |
|---------|------------|
| Search by prompt/filename | Type in search box |
| **Filter by Project** | Select project from dropdown |
| Filter by LoRA | Select "With LoRA" filter |
| Sort by quality | Select "Quality Score" sort |
| Filter by grade | Select grade (A, B+, etc.) |
| Favorites | Click star icon |
| Bulk select | Ctrl/Cmd+click |
| Download ZIP | Select multiple, click Download |

### Project Filter (Primary Way to Organize)

The gallery automatically populates the Project dropdown from:
1. **Metadata project field** - Set via `--project` flag in generate.py
2. **Filename prefix** - Pattern `projectname_YYYYMMDD_...` extracts project name

**Use the Project dropdown to:**
- View only "youngboh" images during character design
- Filter to "nsfw" for NSFW experiments
- Focus on a specific batch without other content

### Filtering Examples

| Task | How |
|------|-----|
| View all youngboh images | Project dropdown → "youngboh" |
| View best youngboh images | Project: "youngboh" + Sort: "Quality Score" |
| Search specific content | Type in search box (searches prompt AND filename) |
| View images with LoRAs | Filter dropdown → "With LoRA" |

### Recommended Workflow for Reviewing Results

1. **Quick filter by project:**
   - Open gallery at `http://192.168.1.162:8080`
   - Select project from dropdown (e.g., "youngboh")
   - Sort by quality score

2. **Star favorites** while browsing

3. **Filter to favorites** to review shortlist

4. **Download selected** as ZIP for further use

---

## Consuming Results

### For Quick Review

After batch completes, agent provides top 5 by score. User can:
- Click directly to view each
- Open gallery with project filter

### For Detailed Analysis

```python
# Load results JSON
import json
with open('youngboh_batch_results.json') as f:
    results = json.load(f)

# Find best by score
best = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:10]
for r in best:
    print(f"Score {r['score']}: {r['url']}")
    print(f"  Pose: {r.get('pose')}, Expression: {r.get('expression')}")
```

### For MLflow Tracking

If experiments need permanent tracking:
```bash
python3 generate.py \
    --workflow workflows/illustrious-anime.json \
    --prompt "..." \
    --mlflow-log \
    --mlflow-experiment "youngboh-characters" \
    --output /tmp/test.png
```

This logs to MLflow at http://192.168.1.162:5001 with full parameter capture.

---

## Workflow Selection Guide

| Subject Type | Workflow | Notes |
|--------------|----------|-------|
| Anime characters | `workflows/illustrious-anime.json` | Use Illustrious model |
| Photorealistic | `workflows/flux-dev.json` | General purpose |
| NSFW photorealistic | `workflows/pornmaster-pony-stacked-realism.json` | Adult content |
| NSFW SD 1.5 | `workflows/nsfw-majicmix.json` | SD 1.5 based |
| Video | `workflows/wan22-t2v.json` | Text-to-video |
| Image-to-video | `workflows/wan22-i2v.json` | Animate images |
  "variation_a": "standing pose",
  "variation_b": "happy expression",
  "lora": "style_lora:0.5",
  "url": "http://192.168.1.215:9000/comfy-gen/...",
  "score": 0.672,
  "returncode": 0
}
```

---

## Common Negative Prompts by Category

### Anime Characters (SFW)
```
blurry, distorted, bad anatomy, extra limbs, watermark, text, 
realistic, photorealistic, 3d render, photography
```

### African-American Characters (Anime)
```
thin lips, narrow nose, European features, Asian features, 
pale skin, light skin, white person, caucasian,
realistic, photorealistic, 3d render, photography,
blurry, distorted, bad anatomy, extra limbs, watermark, text
```

### Character Design (prevent wrong gender)
```
female, woman, girl, feminine, breasts, makeup, jewelry
```
(or swap for male if generating female character)

### Clothing Artifacts
```
stickers, patches, badges, logos, text on clothes
```

### Age-related
```
child, kid, aged, wrinkled, mature face, weathered, 
old looking, middle-aged, 30s, 40s, gaunt, hollow cheeks
```

---

## Generation Parameters Quick Reference

| Parameter | Draft | Standard | High Quality |
|-----------|-------|----------|--------------|
| Steps | 30 | 40-50 | 70 |
| CFG | 7.0 | 7.5 | 8.0 |
| Timeout | 60s | 120s | 180s |

---

## Experiment Logging (MLflow)

For experiments that need tracking, log to MLflow:

```python
from comfy_gen.mlflow_logger import log_experiment, log_batch

# Log single experiment
log_experiment(
    run_name="character_v1",
    image_url="http://...",
    params={
        "checkpoint": "model_name",
        "workflow": "workflow.json",
        "steps": 50,
        "cfg": 7.5,
        "loras": "lora_name:0.5",
        "prompt": "full prompt text",
        "negative_prompt": "full negative",
    },
    validation_score=0.67,
    user_rating=4,
    feedback="Notes about quality",
)
```

---

## Troubleshooting

### Generation Stuck
- Check ComfyUI status: `curl http://192.168.1.215:8188/system_stats`
- Check moira is awake: `ping 192.168.1.215`

### Too Many Failures
- Reduce batch size
- Increase timeout
- Check GPU memory on moira

### Poor Quality Results
- Increase steps (50-70)
- Adjust CFG (7.5-8.5)
- Review prompt structure
- Check LoRA compatibility with workflow

---

## Example Session

**User:** "Run 50 variations of the protagonist character with different poses and expressions"

**Agent Response:**
1. Identify: Character batch generation
2. Gather from context:
   - Character: protagonist (from Framework.md or prior context)
   - Workflow: illustrious-anime.json (anime style)
   - Variations: poses + expressions
3. Create batch script with:
   - BASE_CHARACTER = "[full description]"
   - POSES = [10 variations]
   - EXPRESSIONS = [5 variations]
   - Test with/without style LoRA
4. Run: `python3 scripts/batch_[project]_chars.py`
5. Return ALL URLs when complete
