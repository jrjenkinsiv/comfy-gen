#!/usr/bin/env python3
"""
High-quality Pony Realism batch generation with:
- Higher resolution (1024x1024)
- More steps (40-50)
- Variable LoRA strength (0.6-1.0)
- Diverse scenarios
- Support for Real Cum SDXL LoRA

Usage:
    python3 scripts/batch_pony_hq.py [start] [count]
    python3 scripts/batch_pony_hq.py 1 20  # Generate all 20 images
"""

import subprocess
import sys
import random
import os

# Base config
WORKFLOW = "workflows/pony-realism.json"
BASE_LORA = "zy_AmateurStyle_v2.safetensors"
CUM_LORA = "realcumv6.55.safetensors"
PALE_SKIN_LORA = "Pale_Skin_SDXL_v1.0.safetensors"

# Higher quality settings
STEPS_RANGE = (40, 50)
CFG = 6
RESOLUTION = "1024x1024"

# Quality/style prefixes
QUALITY_PREFIX = "score_9, score_8_up, score_7_up, rating_explicit"
STYLE_TAGS = "photo, grainy, amateur, 2000s nostalgia, webcam photo"
NEGATIVE = "score_1, score_2, score_3, text, watermark, cartoon, anime, drawing, illustration, 3d render, CGI"

# Diverse scenarios with LoRA combos
SCENARIOS = [
    # Solo/tease - Amateur only
    {
        "name": "solo_tease_ass",
        "prompt": "1girl, nude, (ass focus:1.3), (from behind:1.2), woman, bent over, looking back at viewer, bedroom, natural lighting, (detailed skin:1.2)",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "solo_tits_natural",
        "prompt": "1girl, nude, (large natural breasts:1.3), (frontal view:1.2), woman, lying on bed, looking at viewer, soft lighting, (realistic skin texture:1.2)",
        "loras": [(BASE_LORA, "{strength}"), (PALE_SKIN_LORA, "0.4")],
    },
    {
        "name": "solo_spread",
        "prompt": "1girl, nude, (spread legs:1.3), (pussy focus:1.2), woman, on back, bedroom, POV, natural lighting",
        "loras": [(BASE_LORA, "{strength}")],
    },
    
    # Blowjob scenes - Amateur + Cum for cum variants
    {
        "name": "blowjob_pov",
        "prompt": "1girl, (blowjob:1.4), (pov:1.3), nude, woman, on knees, (eye contact:1.2), bedroom, amateur photo",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "blowjob_pov_cum",
        "prompt": "1girl, (blowjob:1.3), (cum on face:1.4), (cum in mouth:1.3), (pov:1.2), nude, woman, (facial:1.3), messy, bedroom",
        "loras": [(BASE_LORA, "{strength}"), (CUM_LORA, "0.7")],
    },
    {
        "name": "deepthroat_side",
        "prompt": "1girl, (deepthroat:1.4), (side view:1.2), nude, woman, (cock in mouth:1.3), bedroom, grainy photo",
        "loras": [(BASE_LORA, "{strength}")],
    },
    
    # Doggy scenes
    {
        "name": "doggy_pov",
        "prompt": "1girl, (doggystyle:1.4), (pov:1.3), nude, woman, (from behind:1.2), (ass up:1.2), bedroom, on bed",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "doggy_side",
        "prompt": "1girl, 1boy, (doggystyle:1.4), (side view:1.2), nude, woman, (sex:1.3), bedroom, amateur",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "prone_bone",
        "prompt": "1girl, 1boy, (prone bone:1.4), nude, woman, (lying flat:1.2), (sex from behind:1.3), on bed, amateur photo",
        "loras": [(BASE_LORA, "{strength}")],
    },
    
    # Missionary
    {
        "name": "missionary_pov",
        "prompt": "1girl, (missionary:1.4), (pov:1.3), nude, woman, (legs spread:1.2), on back, bedroom, eye contact",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "missionary_legs_up",
        "prompt": "1girl, 1boy, (missionary:1.4), (legs up:1.3), nude, woman, (sex:1.3), on bed, passionate",
        "loras": [(BASE_LORA, "{strength}")],
    },
    
    # Cowgirl
    {
        "name": "cowgirl_pov",
        "prompt": "1girl, (cowgirl position:1.4), (pov:1.3), nude, woman, (riding:1.3), (bouncing breasts:1.2), bedroom",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "reverse_cowgirl",
        "prompt": "1girl, (reverse cowgirl:1.4), (pov:1.3), nude, woman, (ass focus:1.2), (riding:1.3), bedroom",
        "loras": [(BASE_LORA, "{strength}")],
    },
    
    # Cumshots - Use Real Cum LoRA
    {
        "name": "facial_cumshot",
        "prompt": "1girl, (cum on face:1.5), (facial:1.4), (thick cum:1.3), nude, woman, (cum dripping:1.2), messy, bedroom, after sex",
        "loras": [(BASE_LORA, "{strength}"), (CUM_LORA, "0.8")],
    },
    {
        "name": "cumshot_tits",
        "prompt": "1girl, (cum on breasts:1.5), (cum on tits:1.4), nude, woman, (large breasts:1.2), (cum dripping:1.3), after sex, bedroom",
        "loras": [(BASE_LORA, "{strength}"), (CUM_LORA, "0.8")],
    },
    {
        "name": "cumshot_body",
        "prompt": "1girl, (cum on body:1.5), (cum on stomach:1.4), nude, woman, lying down, (messy:1.3), after sex, bedroom",
        "loras": [(BASE_LORA, "{strength}"), (CUM_LORA, "0.8")],
    },
    {
        "name": "creampie",
        "prompt": "1girl, (creampie:1.5), (cum dripping from pussy:1.4), nude, woman, (legs spread:1.2), on back, bedroom, after sex",
        "loras": [(BASE_LORA, "{strength}"), (CUM_LORA, "0.7")],
    },
    
    # Other positions
    {
        "name": "standing_sex",
        "prompt": "1girl, 1boy, (standing sex:1.4), (from behind:1.3), nude, woman, (against wall:1.2), bathroom, amateur photo",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "titfuck",
        "prompt": "1girl, (titfuck:1.4), (paizuri:1.3), (pov:1.2), nude, woman, (large breasts:1.3), bedroom",
        "loras": [(BASE_LORA, "{strength}")],
    },
    {
        "name": "69_position",
        "prompt": "1girl, 1boy, (69 position:1.4), nude, (oral sex:1.3), bedroom, amateur photo",
        "loras": [(BASE_LORA, "{strength}")],
    },
]

# Body type and ethnicity variations
BODY_TYPES = [
    "slim body", "curvy body", "athletic body", "busty", 
    "thicc thighs", "milf body", "petite", "hourglass figure"
]

ETHNICITIES = [
    "caucasian woman", "latina woman", "asian woman", "black woman",
    "mixed race woman", "redhead woman", "brunette woman", "blonde woman"
]

# LoRA strength variations
STRENGTH_VARIATIONS = [0.6, 0.7, 0.8, 0.9, 1.0]


def generate_image(idx: int, scenario: dict, body: str, ethnicity: str, strength: float) -> bool:
    """Generate a single high-quality image."""
    
    # Build prompt
    prompt = f"{QUALITY_PREFIX}, {STYLE_TAGS}, {scenario['prompt']}, {body}, {ethnicity}"
    
    # Build LoRA arguments (multiple --lora flags)
    lora_args = []
    for lora_file, lora_str in scenario['loras']:
        if lora_str == "{strength}":
            lora_args.extend(["--lora", f"{lora_file}:{strength}"])
        else:
            lora_args.extend(["--lora", f"{lora_file}:{lora_str}"])
    
    # Random steps in range
    steps = random.randint(*STEPS_RANGE)
    seed = random.randint(1, 999999)
    
    output_name = f"pony_hq_{idx:03d}_{scenario['name']}"
    output_path = f"/tmp/{output_name}.png"
    
    cmd = [
        "python3", "generate.py",
        "--workflow", WORKFLOW,
        "--prompt", prompt,
        "--negative-prompt", NEGATIVE,
        "--steps", str(steps),
        "--cfg", str(CFG),
    ] + lora_args + [
        "--seed", str(seed),
        "--output", output_path
    ]
    
    print(f"\n[{idx:03d}] {scenario['name']} | {body} | {ethnicity}")
    print(f"      LoRA strength: {strength} | Steps: {steps}")
    print(f"      LoRAs: {[a for a in lora_args if not a.startswith('--')]}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        if result.returncode == 0:
            # Extract CLIP score if present
            for line in result.stdout.split('\n'):
                if 'CLIP' in line or 'score' in line.lower():
                    print(f"      {line.strip()}")
            print(f"      [OK] Generated: {output_name}")
            return True
        else:
            print(f"      [ERROR] {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"      [ERROR] {e}")
        return False


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    print(f"=== Pony Realism HQ Batch Generation ===")
    print(f"Generating images {start} to {start + count - 1}")
    print(f"Steps: {STEPS_RANGE[0]}-{STEPS_RANGE[1]}, CFG: {CFG}")
    print(f"LoRA strength variations: {STRENGTH_VARIATIONS}")
    print(f"Scenarios: {len(SCENARIOS)}")
    
    successes = 0
    failures = 0
    
    for i in range(start, start + count):
        # Cycle through scenarios
        scenario = SCENARIOS[(i - 1) % len(SCENARIOS)]
        
        # Random body/ethnicity
        body = random.choice(BODY_TYPES)
        ethnicity = random.choice(ETHNICITIES)
        
        # Variable LoRA strength
        strength = random.choice(STRENGTH_VARIATIONS)
        
        if generate_image(i, scenario, body, ethnicity, strength):
            successes += 1
        else:
            failures += 1
    
    print(f"\n=== Complete ===")
    print(f"Success: {successes}, Failures: {failures}")
    print(f"Images at: http://192.168.1.215:9000/comfy-gen/")
    print(f"Gallery at: http://192.168.1.162:8080/")


if __name__ == "__main__":
    main()
