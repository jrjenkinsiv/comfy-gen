#!/usr/bin/env python3
"""
Batch Explicit NSFW Generation - V2 (Improved Prompting)

FIXES FROM V1:
1. Floating cocks: POV-only for scenes with male anatomy (no visible male body)
2. Multi-figure chaos: Avoid two-figure scenes entirely, OR use very specific composition
3. Better LoRA usage: Penis LoRAs only for POV shots where cock is the focus

STRATEGY:
- Solo female poses: No issues, keep as-is but add more detail
- Oral/cock scenes: ONLY POV angle (viewer's cock), never show full male body
- Facial/cum scenes: Post-act, no male needed in frame
- Positions: Solo poses "waiting" or POV penetration hints

The key insight: SD 1.5 cannot reliably generate two distinct human bodies.
POV shots hide the male body entirely - the cock becomes "the viewer's cock".
"""

import subprocess
import random
import sys
from pathlib import Path
from datetime import datetime

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Ethnicities - Asian focus as requested
ETHNICITIES = [
    # East Asian
    "japanese", "korean", "chinese", "vietnamese", "thai", "filipino", 
    "taiwanese", "singaporean", "malaysian", "indonesian",
    # South Asian  
    "indian", "pakistani", "bangladeshi", "sri lankan", "nepali",
    # Middle Eastern
    "persian", "arab", "lebanese", "turkish",
]

# =============================================================================
# SCENARIO TEMPLATES - V2 IMPROVED
# =============================================================================
# Key changes:
# - All cock scenes are POV (no male body visible)
# - More detailed spatial/compositional prompts
# - Redundant emphasis on single subject where needed
# - Better negative prompts

SCENARIOS = [
    # -----------------------------------------
    # SOLO NUDE - These work well, keep similar
    # -----------------------------------------
    {
        "name": "nude_standing",
        "category": "solo",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "professional boudoir photograph of beautiful {ethnicity} woman in her early 20s, "
            "solo subject, completely naked nude, elegant standing pose with one hand on hip, "
            "natural medium breasts with small erect nipples, flat toned stomach, "
            "shaved pussy visible between slightly parted legs, "
            "full body shot centered in frame, looking at camera with confident seductive expression, "
            "soft diffused studio lighting from above and side, clean neutral background, "
            "photorealistic skin texture with visible pores and subtle imperfections, "
            "professional photography, sharp focus on subject, shallow depth of field, 8k uhd"
        ),
        "negative": (
            "multiple people, two people, crowd, group, duplicate, clone, extra person, "
            "clothes, clothed, dressed, bikini, underwear, "
            "bad anatomy, deformed, ugly, blurry, low quality, "
            "cartoon, anime, painting, illustration, cgi, 3d render"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
        "uses_penis_lora": False
    },
    {
        "name": "nude_lying_bed",
        "category": "solo",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "professional photograph of gorgeous {ethnicity} woman, solo subject, "
            "fully nude naked lying on white silk bed sheets, "
            "on her back with one knee slightly raised, arms relaxed at sides, "
            "natural breasts with erect nipples, legs slightly parted showing pussy, "
            "sensual relaxed pose, head on pillow looking at camera, "
            "luxury bedroom setting with soft window light from left side, "
            "photorealistic skin detail with pores and subtle imperfections, "
            "intimate boudoir photography style, shallow depth of field, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, two people, duplicate, clone, "
            "clothes, clothed, dressed, underwear, standing, sitting, "
            "bad anatomy, deformed, ugly, blurry, cartoon, anime, painting, cgi"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
        "uses_penis_lora": False
    },
    {
        "name": "nude_kneeling",
        "category": "solo",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "professional photograph of stunning {ethnicity} woman, solo subject, "
            "completely nude, kneeling pose on bed with knees apart, "
            "sitting back on her heels, hands resting on thighs, "
            "perky natural breasts with visible nipples, "
            "smooth shaved vulva visible from kneeling position, "
            "looking up at camera with submissive seductive expression, "
            "soft warm lighting from above, clean background, "
            "photorealistic skin texture, professional erotic photography, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, two people, duplicate, clone, extra person, "
            "clothes, dressed, underwear, standing, lying, "
            "bad anatomy, deformed, cartoon, anime, blurry, cgi"
        ),
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
        "uses_penis_lora": False
    },
    
    # -----------------------------------------
    # POV ORAL - Cock visible, no male body
    # Key: Camera is the viewer, cock enters from bottom of frame
    # -----------------------------------------
    {
        "name": "pov_blowjob",
        "category": "pov_oral",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view looking down, "
            "beautiful {ethnicity} woman on her knees, nude naked, "
            "sucking viewer's large erect cock, penis in her mouth, "
            "cock entering frame from bottom edge (viewer's body), "
            "her face looking up at camera while sucking dick, "
            "eye contact with camera, her hands on the shaft, "
            "natural breasts visible below, "
            "soft lighting from above, photorealistic detail, sharp focus, 8k uhd"
        ),
        "negative": (
            "side view, third person view, full male body visible, man visible, "
            "multiple women, two women, duplicate woman, "
            "clothes, bad anatomy, cartoon, anime, blurry, "
            "soft penis, flaccid, deformed cock"
        ),
        "loras": [("erect_penis_epoch_80.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_licking",
        "category": "pov_oral",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view, "
            "gorgeous {ethnicity} woman licking viewer's large erect cock, "
            "tongue out touching shaft of penis, "
            "cock entering frame from bottom (viewer's perspective), "
            "looking up at camera seductively while licking dick, "
            "nude naked with breasts visible, "
            "oral foreplay, teasing expression, "
            "soft lighting, photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "side view, third person, full male body, man's body visible, "
            "multiple women, duplicate, clothes, "
            "bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.5), ("realora_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_deepthroat",
        "category": "pov_oral",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view looking down, "
            "nude {ethnicity} woman deepthroating viewer's large erect cock, "
            "penis deep in her throat, mouth stretched around dick, "
            "cock entering from bottom of frame (viewer's body), "
            "eyes watering, slobber and drool on chin, "
            "looking up at camera while deepthroating, "
            "breasts visible below, "
            "explicit deepthroat oral sex, photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "side view, third person, man's body visible, standing man, "
            "multiple women, duplicate, clothes, "
            "bad anatomy, cartoon, anime, blurry, soft penis, flaccid, deformed"
        ),
        "loras": [("erect_penis_epoch_80.safetensors", 0.55), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    
    # -----------------------------------------
    # POV HANDJOB/TITJOB - Same POV principle
    # -----------------------------------------
    {
        "name": "pov_handjob",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view, "
            "beautiful nude {ethnicity} woman giving handjob, "
            "her hand wrapped around viewer's large erect cock, "
            "stroking dick, cock entering frame from bottom edge, "
            "looking up at camera seductively while jerking, "
            "breasts visible, sitting or kneeling position, "
            "first person view handjob, photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "side view, third person, man visible, full male body, "
            "clothes, bad anatomy, cartoon, anime, blurry, "
            "soft penis, flaccid, deformed"
        ),
        "loras": [("erect_penis_epoch_80.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_titjob",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view looking down, "
            "nude {ethnicity} woman pressing her breasts around viewer's erect cock, "
            "penis between her tits, titfuck titjob, "
            "cock entering frame from bottom (viewer's body), "
            "looking up at camera seductively while giving titfuck, "
            "natural medium-large breasts squeezing dick, "
            "first person view, photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "side view, third person, man visible, male body, "
            "small breasts, flat chest, clothes, "
            "bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    
    # -----------------------------------------
    # POST-ACT CUM SHOTS - No male in frame at all
    # The cum is already there, male has stepped away
    # -----------------------------------------
    {
        "name": "facial_cum",
        "category": "cum",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "explicit photograph of beautiful {ethnicity} woman, solo subject, "
            "face covered in thick white cum semen, "
            "fresh cum dripping from chin and cheeks, mouth open tongue out with cum, "
            "freshly cummed on, satisfied slutty expression, "
            "nude naked with breasts visible, kneeling pose, "
            "messy facial cumshot result, just received facial, "
            "looking at camera, no male visible in frame, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis, cock visible, "
            "clean face, no cum, clothes, "
            "bad anatomy, deformed, ugly, cartoon, anime, blurry"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
        "uses_penis_lora": False
    },
    {
        "name": "cum_mouth",
        "category": "cum",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "explicit photograph of gorgeous {ethnicity} woman, solo subject, "
            "thick white cum in open mouth, semen on lips and tongue visible, "
            "just received oral cumshot, mouth open showing cum inside, "
            "nude kneeling, breasts visible, "
            "looking at camera while showing cum in mouth, "
            "satisfied expression, no male in frame, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis, cock, "
            "clean mouth, no cum, closed mouth, clothes, "
            "bad anatomy, cartoon, anime, blurry"
        ),
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
        "uses_penis_lora": False
    },
    {
        "name": "cum_tits",
        "category": "cum",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "explicit photograph of stunning nude {ethnicity} woman, solo subject, "
            "thick white cum on her breasts, semen dripping between tits, "
            "cum covered chest and nipples, freshly cummed on, "
            "looking down at her messy breasts with satisfied smile, "
            "no male visible in frame, just the result, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis visible, cock, "
            "clean breasts, no cum, clothes, "
            "bad anatomy, deformed, cartoon, anime, blurry"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)],
        "uses_penis_lora": False
    },
    
    # -----------------------------------------
    # SOLO POSES - "WAITING" positions (no male)
    # -----------------------------------------
    {
        "name": "doggy_waiting",
        "category": "solo_pose",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "explicit photograph of beautiful nude {ethnicity} woman, solo subject, "
            "on all fours doggy style position on bed, ass up face down, "
            "looking back over shoulder at camera seductively, "
            "pussy visible from behind, arched back, "
            "waiting pose as if inviting, no other person in frame, "
            "on white silk sheets, soft lighting, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis, cock, second person, "
            "clothes, standing, lying flat, "
            "bad anatomy, cartoon, anime, blurry, deformed"
        ),
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
        "uses_penis_lora": False
    },
    {
        "name": "spread_presenting",
        "category": "solo_pose",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "explicit photograph of gorgeous nude {ethnicity} woman, solo subject, "
            "lying on back on bed, legs spread wide open, "
            "hands holding thighs apart showing pink wet pussy, "
            "natural breasts, inviting presentation pose, "
            "looking at camera with seductive expression, "
            "no other person in frame, "
            "on white silk sheets, soft lighting, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis, second person, "
            "clothes, legs closed, standing, "
            "bad anatomy, cartoon, anime, blurry, deformed"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)],
        "uses_penis_lora": False
    },
    {
        "name": "breast_present",
        "category": "solo_pose",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "professional photograph close up of beautiful {ethnicity} woman, solo subject, "
            "presenting her perfect natural breasts, medium size round perky tits, "
            "hands cupping and squeezing breasts together, erect nipples, "
            "looking at camera seductively, topless upper body focus, "
            "smooth realistic skin texture with visible pores, "
            "soft natural lighting, photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, full body, "
            "clothes, bra, bad anatomy, deformed nipples, "
            "cartoon, anime, blurry, fake looking, implants"
        ),
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)],
        "uses_penis_lora": False
    },
]

# Resolutions - portrait for body shots
RESOLUTIONS = [
    (768, 1152),   # Standard portrait
    (768, 1280),   # Tall portrait
    (832, 1216),   # Wider portrait
]


def generate_image(idx: int, ethnicity: str, scenario: dict, resolution: tuple, seed: int):
    """Generate a single image."""
    prompt = scenario["prompt"].format(ethnicity=ethnicity)
    negative = scenario["negative"]
    scenario_name = scenario["name"]
    loras = scenario.get("loras", [])
    
    width, height = resolution
    
    # Build filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eth_short = ethnicity.replace(" ", "_")[:10]
    
    output_name = f"{timestamp}_explicit_v2_{idx:03d}_{eth_short}_{scenario_name}"
    output_path = f"/tmp/{output_name}.png"
    
    # Build command
    cmd = [
        "python3", "generate.py",
        "--workflow", "workflows/majicmix-realistic.json",
        "--prompt", prompt,
        "--negative-prompt", negative,
        "--steps", "60",
        "--cfg", "9",
        "--seed", str(seed),
        "--width", str(width),
        "--height", str(height),
        "--output", output_path,
    ]
    
    # Add LoRAs from scenario
    for lora_file, strength in loras:
        cmd.extend(["--lora", f"{lora_file}:{strength}"])
    
    print(f"\n[{idx:03d}] {ethnicity} - {scenario_name}")
    print(f"  Resolution: {width}x{height}, Seed: {seed}")
    print(f"  Category: {scenario['category']}")
    print(f"  LoRAs: {loras}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd="/Users/jrjenkinsiv/Development/comfy-gen"
        )
        
        if result.returncode == 0:
            # Extract URL from output
            url = None
            for line in result.stdout.split('\n'):
                if 'http://192.168.1.215:9000/comfy-gen/' in line:
                    url = line.strip().split()[-1]
            print(f"  [OK] {url or 'Generated'}")
            return True, url
        else:
            print(f"  [ERROR] {result.stderr[-300:] if result.stderr else 'Unknown error'}")
            return False, None
            
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] Generation took too long")
        return False, None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False, None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch explicit generation V2 - improved prompts")
    parser.add_argument("--count", type=int, default=50, help="Number of images to generate")
    parser.add_argument("--start", type=int, default=1, help="Starting index")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--category", type=str, help="Only generate specific category (solo, pov_oral, pov_touch, cum, solo_pose)")
    parser.add_argument("--list", action="store_true", help="List all scenarios")
    args = parser.parse_args()
    
    if args.list:
        print("Available scenarios:")
        print("-" * 60)
        for s in SCENARIOS:
            print(f"  {s['name']:20s} [{s['category']}] penis_lora={s['uses_penis_lora']}")
        return
    
    print("=" * 60)
    print("Explicit NSFW Batch Generation - V2 (Improved Prompts)")
    print("=" * 60)
    print("Key improvements:")
    print("  - POV-only for cock scenes (no floating cocks)")
    print("  - Single subject emphasis for all scenes")
    print("  - Post-act cum shots (no male in frame)")
    print("=" * 60)
    
    # Filter scenarios if category specified
    scenarios = SCENARIOS
    if args.category:
        scenarios = [s for s in SCENARIOS if s['category'] == args.category]
        print(f"Filtered to category: {args.category} ({len(scenarios)} scenarios)")
    
    # Build generation queue
    queue = []
    idx = args.start
    
    # Cycle through ethnicities and scenarios
    while len(queue) < args.count:
        for scenario in scenarios:
            if len(queue) >= args.count:
                break
            ethnicity = random.choice(ETHNICITIES)
            resolution = random.choice(RESOLUTIONS)
            seed = random.randint(1, 999999)
            queue.append((idx, ethnicity, scenario, resolution, seed))
            idx += 1
    
    print(f"\nGenerating {len(queue)} images...")
    print(f"Estimated time: {len(queue) * 1.5:.0f} minutes")
    
    success = 0
    failed = 0
    urls = []
    
    for item in queue:
        idx, ethnicity, scenario, resolution, seed = item
        
        if args.dry_run:
            print(f"\n[DRY RUN] {idx}: {ethnicity} - {scenario['name']}")
            continue
            
        ok, url = generate_image(idx, ethnicity, scenario, resolution, seed)
        if ok:
            success += 1
            if url:
                urls.append(url)
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    
    if urls:
        print(f"\nGenerated URLs (last 10):")
        for url in urls[-10:]:
            print(f"  {url}")


if __name__ == "__main__":
    main()
