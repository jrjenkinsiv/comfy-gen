#!/usr/bin/env python3
"""
Batch generation using Pony Realism + Amateur LoRA
The winning combination for photorealistic NSFW content
"""

import random
import subprocess
import sys
import time

# Configuration
WORKFLOW = "workflows/pony-realism.json"
LORA = "zy_AmateurStyle_v2.safetensors:0.8"
STEPS = 25
CFG = 6
BASE_SEED = 7000

# Prompt components for variety
QUALITY_TAGS = "score_9, score_8_up, score_7_up, rating_explicit"
STYLE_TAGS = "photo, grainy, amateur, 2000s nostalgia, webcam photo"
NEGATIVE = "score_1, score_2, score_3, text, watermark, cartoon, anime, illustration"

# Body types
BODY_TYPES = [
    "slim petite woman",
    "curvy thick woman, wide hips, thick thighs",
    "athletic toned woman, fit body",
    "busty woman, large breasts",
    "thicc woman, big ass, wide hips",
    "milf, mature woman",
    "young woman, petite",
    "hourglass figure woman",
]

# Ethnicities
ETHNICITIES = [
    "caucasian",
    "latina",
    "asian",
    "black",
    "mixed race",
    "redhead, pale skin, freckles",
    "brunette",
    "blonde",
]

# Hair styles
HAIR = [
    "long hair",
    "short hair",
    "ponytail",
    "messy hair",
    "hair down",
]

# Positions/scenarios
SCENARIOS = [
    # Solo
    {
        "name": "ass_bent_over",
        "prompt": "1girl, nude, (ass focus:1.3), (from behind:1.2), bent over, looking back at viewer, {body}, {ethnicity}, {hair}",
        "setting": "bedroom, natural lighting"
    },
    {
        "name": "tits_frontal",
        "prompt": "1girl, nude, (breast focus:1.3), frontal view, large breasts, {body}, {ethnicity}, {hair}, hands on hips",
        "setting": "bedroom, soft lighting"
    },
    {
        "name": "spread_legs",
        "prompt": "1girl, nude, (spread legs:1.3), lying on back, (pussy:1.2), {body}, {ethnicity}, {hair}",
        "setting": "on bed, bedroom"
    },
    {
        "name": "on_knees",
        "prompt": "1girl, nude, kneeling, (on knees:1.2), looking up at viewer, {body}, {ethnicity}, {hair}",
        "setting": "bedroom floor"
    },
    # Blowjob variations
    {
        "name": "blowjob_pov",
        "prompt": "1girl, 1boy, nude, (blowjob:1.3), (pov:1.2), kneeling, (penis in mouth:1.3), deepthroat, saliva, (looking up at viewer:1.2), hands on penis, {body}, {ethnicity}, {hair}",
        "setting": "bedroom, natural lighting"
    },
    {
        "name": "blowjob_side",
        "prompt": "1girl, 1boy, nude, (blowjob:1.3), (side view:1.2), kneeling, (oral:1.2), saliva, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "deepthroat",
        "prompt": "1girl, 1boy, nude, (deepthroat:1.4), (pov:1.2), (penis in mouth:1.3), saliva dripping, tears, mascara running, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    # Doggy variations
    {
        "name": "doggy_pov",
        "prompt": "1girl, 1boy, nude, (doggy style:1.3), (from behind:1.2), (sex:1.3), (pov:1.2), penetration, ass up, face down, {body}, {ethnicity}, {hair}",
        "setting": "on bed, bedroom"
    },
    {
        "name": "doggy_side",
        "prompt": "1girl, 1boy, nude, (doggy style:1.3), (side view:1.2), (sex:1.3), penetration, on all fours, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "prone_bone",
        "prompt": "1girl, 1boy, nude, (prone bone:1.3), lying flat, (sex from behind:1.3), (penetration:1.2), {body}, {ethnicity}, {hair}",
        "setting": "on bed"
    },
    # Missionary variations
    {
        "name": "missionary_pov",
        "prompt": "1girl, 1boy, nude, (missionary:1.3), (pov:1.2), (sex:1.3), legs spread, penetration, looking up at viewer, {body}, {ethnicity}, {hair}",
        "setting": "on bed, bedroom"
    },
    {
        "name": "missionary_legs_up",
        "prompt": "1girl, 1boy, nude, (missionary:1.3), (legs up:1.2), (sex:1.3), penetration, ankles near head, {body}, {ethnicity}, {hair}",
        "setting": "on bed"
    },
    # Cowgirl variations
    {
        "name": "cowgirl_pov",
        "prompt": "1girl, 1boy, nude, (cowgirl position:1.3), (pov:1.2), (riding:1.2), (sex:1.3), on top, bouncing, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "reverse_cowgirl",
        "prompt": "1girl, 1boy, nude, (reverse cowgirl:1.3), (pov:1.2), (riding:1.2), (ass:1.2), looking back, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    # Cumshot variations
    {
        "name": "facial_cumshot",
        "prompt": "1girl, 1boy, nude, (facial:1.4), (cumshot:1.3), (cum on face:1.3), eyes closed, mouth open, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "cum_in_mouth",
        "prompt": "1girl, 1boy, nude, (cum in mouth:1.4), (cumshot:1.3), mouth open, tongue out, swallowing, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "cumshot_tits",
        "prompt": "1girl, 1boy, nude, (cum on breasts:1.4), (cumshot:1.3), large breasts, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "cumshot_ass",
        "prompt": "1girl, 1boy, nude, (cum on ass:1.4), (cumshot:1.3), bent over, (ass focus:1.2), {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "creampie",
        "prompt": "1girl, 1boy, nude, (creampie:1.4), (cum dripping:1.3), (pussy:1.2), after sex, {body}, {ethnicity}, {hair}",
        "setting": "on bed"
    },
    # Other positions
    {
        "name": "standing_fuck",
        "prompt": "1girl, 1boy, nude, (standing sex:1.3), (from behind:1.2), (against wall:1.2), penetration, {body}, {ethnicity}, {hair}",
        "setting": "against wall, bedroom"
    },
    {
        "name": "titfuck",
        "prompt": "1girl, 1boy, nude, (paizuri:1.3), (titfuck:1.3), (penis between breasts:1.3), large breasts, looking up, {body}, {ethnicity}, {hair}",
        "setting": "bedroom"
    },
    {
        "name": "69_position",
        "prompt": "1girl, 1boy, nude, (69 position:1.3), (oral:1.2), (cunnilingus:1.2), (blowjob:1.2), {body}, {ethnicity}, {hair}",
        "setting": "on bed"
    },
    # Shower/bathroom
    {
        "name": "shower_solo",
        "prompt": "1girl, nude, (shower:1.2), wet body, wet hair, water droplets, {body}, {ethnicity}, {hair}",
        "setting": "bathroom, shower, steam"
    },
    {
        "name": "shower_sex",
        "prompt": "1girl, 1boy, nude, (shower sex:1.3), wet bodies, (from behind:1.2), against shower wall, {body}, {ethnicity}, {hair}",
        "setting": "shower, bathroom, wet"
    },
]

def generate_prompt(scenario: dict) -> tuple[str, str]:
    """Generate a full prompt with random variations"""
    body = random.choice(BODY_TYPES)
    ethnicity = random.choice(ETHNICITIES)
    hair = random.choice(HAIR)

    # Build prompt
    base_prompt = scenario["prompt"].format(body=body, ethnicity=ethnicity, hair=hair)
    setting = scenario["setting"]

    full_prompt = f"{QUALITY_TAGS}, {STYLE_TAGS}, {base_prompt}, {setting}"

    return full_prompt, scenario["name"]


def run_generation(prompt: str, name: str, seed: int, index: int):
    """Run a single generation"""
    output_file = f"/tmp/pony_batch_{index:03d}_{name}.png"

    cmd = [
        "python3", "generate.py",
        "--workflow", WORKFLOW,
        "--prompt", prompt,
        "--negative-prompt", NEGATIVE,
        "--steps", str(STEPS),
        "--cfg", str(CFG),
        "--lora", LORA,
        "--seed", str(seed),
        "--output", output_file
    ]

    print(f"\n[{index}/100] Generating: {name} (seed {seed})")
    print(f"  Prompt: {prompt[:80]}...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # Extract score from output
        for line in result.stdout.split('\n'):
            if 'Score:' in line:
                print(f"  {line.strip()}")
                break
            if 'Image available at:' in line:
                url = line.split(': ')[1].strip()
                print(f"  URL: {url}")
        return True
    else:
        print("  [ERROR] Generation failed")
        print(result.stderr[-500:] if result.stderr else "No error output")
        return False


def main():
    print("=" * 60)
    print("PONY REALISM BATCH GENERATION")
    print("=" * 60)
    print(f"Workflow: {WORKFLOW}")
    print(f"LoRA: {LORA}")
    print(f"Steps: {STEPS}, CFG: {CFG}")
    print("=" * 60)

    # Parse arguments
    start_index = 1
    count = 100

    if len(sys.argv) > 1:
        start_index = int(sys.argv[1])
    if len(sys.argv) > 2:
        count = int(sys.argv[2])

    print(f"Generating {count} images starting from index {start_index}")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for i in range(start_index, start_index + count):
        # Pick random scenario
        scenario = random.choice(SCENARIOS)
        prompt, name = generate_prompt(scenario)
        seed = BASE_SEED + i

        try:
            if run_generation(prompt, name, seed, i):
                success_count += 1
            else:
                fail_count += 1
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"  [ERROR] {e}")
            fail_count += 1

        # Small delay between generations
        time.sleep(1)

    print("\n" + "=" * 60)
    print(f"BATCH COMPLETE: {success_count} success, {fail_count} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
