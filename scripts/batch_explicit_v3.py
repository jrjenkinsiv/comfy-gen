#!/usr/bin/env python3
"""
Batch Explicit NSFW Generation - V3 (Improved Contact/Interaction Prompts)

CRITICAL: LORA SELECTION
=========================
Use SD 1.5 IMAGE LoRAs (~150MB), NOT Wan 2.2 VIDEO LoRAs (~307MB)!

CORRECT (Image LoRAs):
  airoticart_penis.safetensors (151MB) - Use trigger words: penerec (erect), penflac (flaccid)
  polyhedron_skin.safetensors (151MB) - Realistic skin texture
  realora_skin.safetensors (151MB) - Subtle skin enhancement

WRONG (Video LoRAs - DO NOT USE FOR IMAGES):
  erect_penis_epoch_80.safetensors (307MB) - WAN 2.2 VIDEO LORA!
  deepthroat_epoch_80.safetensors (307MB) - WAN 2.2 VIDEO LORA!
  dicks_epoch_100.safetensors (307MB) - WAN 2.2 VIDEO LORA!

IMPROVEMENTS OVER V2:
1. More explicit anatomical contact descriptions
2. Weighted emphasis on key interactions: (lips around cock:1.3), (hand gripping shaft:1.3)
3. Added ball-handling scenarios
4. Specific physical contact markers: "lips sealed around", "fingers wrapped", "tongue pressing"
5. FIXED: Uses correct airoticart_penis LoRA with trigger words

KEY PROMPT PATTERNS FOR CONTACT:
- Oral: "(lips wrapped around cock shaft:1.3)", "(dick inside mouth:1.3)"
- Handjob: "(fingers gripping erect shaft:1.3)", "(hand wrapped around cock:1.3)"
- Balls: "(hand cupping balls:1.3)", "(fingers touching testicles:1.2)"
- Licking: "(tongue touching cock head:1.3)", "(tongue on shaft:1.3)"
"""

import random
import subprocess
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Ethnicities - Asian focus
ETHNICITIES = [
    "japanese", "korean", "chinese", "vietnamese", "thai", "filipino",
    "taiwanese", "singaporean", "malaysian", "indonesian",
    "indian", "pakistani", "bangladeshi", "sri lankan",
    "persian", "arab", "lebanese", "turkish",
]

# =============================================================================
# IMPROVED SCENARIOS WITH EXPLICIT CONTACT DESCRIPTIONS
# =============================================================================

SCENARIOS = [
    # -----------------------------------------
    # SOLO NUDE - Keep from V2, work well
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
            "soft diffused studio lighting, clean neutral background, "
            "photorealistic skin texture with visible pores, professional photography, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, two people, crowd, duplicate, clone, "
            "clothes, clothed, dressed, bikini, underwear, "
            "bad anatomy, deformed, ugly, blurry, cartoon, anime, cgi"
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
            "perky natural breasts with visible nipples, smooth shaved vulva visible, "
            "looking up at camera with submissive seductive expression, "
            "soft warm lighting from above, clean background, "
            "photorealistic skin texture, professional erotic photography, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, two people, duplicate, clone, "
            "clothes, dressed, underwear, standing, lying, "
            "bad anatomy, deformed, cartoon, anime, blurry, cgi"
        ),
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
        "uses_penis_lora": False
    },

    # -----------------------------------------
    # POV ORAL - IMPROVED WITH EXPLICIT CONTACT
    # Key additions: "lips sealed around", "cock inside mouth", weighted emphasis
    # -----------------------------------------
    {
        "name": "pov_blowjob_sucking",
        "category": "pov_oral",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view looking down, "
            "beautiful {ethnicity} woman on her knees giving blowjob, "
            "(lips wrapped tightly around cock shaft:1.3), (dick inside her mouth:1.3), "
            "(sucking cock:1.2), penerec, erect penis, cheeks slightly hollowed from suction, "
            "erect penis entering frame from bottom (viewer's cock), "
            "shaft disappearing between her lips, only base of cock visible, "
            "looking up at camera with cock in mouth, eye contact, "
            "nude naked, natural breasts visible below, "
            "photorealistic detail, sharp focus, 8k uhd"
        ),
        "negative": (
            "cock outside mouth, lips not touching cock, mouth closed, "
            "side view, third person, full male body visible, "
            "multiple women, duplicate, clothes, penflac, soft penis, flaccid, "
            "bad anatomy, cartoon, anime, blurry"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.5)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_deepthroat_contact",
        "category": "pov_oral",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's POV looking down, "
            "nude {ethnicity} woman deepthroating, "
            "(cock deep inside throat:1.3), (lips stretched around thick shaft:1.3), "
            "(entire dick in mouth:1.2), only balls visible at base, "
            "nose nearly touching viewer's pelvis, throat bulging slightly, "
            "eyes watering, tears streaming, drool and slobber, "
            "gagging on cock, looking up while deepthroating, "
            "breasts visible below, "
            "explicit deepthroat, photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "cock outside mouth, shallow blowjob, tip only, "
            "side view, third person, man's body visible, "
            "multiple women, duplicate, clothes, "
            "bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_licking_shaft",
        "category": "pov_oral",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view, "
            "gorgeous {ethnicity} woman licking cock, "
            "(tongue pressing against cock shaft:1.3), (tongue flat on penis:1.3), "
            "(licking from base to tip:1.2), tongue tracing veins, "
            "erect cock entering frame from bottom (viewer's cock), "
            "tongue in direct contact with skin of shaft, "
            "looking up at camera seductively while licking, "
            "nude naked, breasts visible, teasing expression, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "tongue not touching cock, mouth closed, sucking, "
            "side view, third person, full male body, "
            "multiple women, duplicate, clothes, "
            "bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("realora_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_licking_tip",
        "category": "pov_oral",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's POV, "
            "beautiful {ethnicity} woman licking cock head, "
            "(tongue touching glans:1.3), (tongue on cock tip:1.3), "
            "(licking head of penis:1.2), tongue circling the tip, "
            "erect cock entering frame from bottom, "
            "tongue making direct contact with cockhead, "
            "mouth open, playful teasing lick, looking up at camera, "
            "nude, breasts visible, seductive expression, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "tongue not touching, mouth closed, cock in mouth, "
            "side view, third person, male body visible, "
            "multiple women, duplicate, clothes, "
            "bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },

    # -----------------------------------------
    # POV HANDJOB - IMPROVED WITH GRIP CONTACT
    # Key additions: "fingers wrapped around", "hand gripping", "stroking motion"
    # -----------------------------------------
    {
        "name": "pov_handjob_grip",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view, "
            "beautiful nude {ethnicity} woman giving handjob, "
            "(fingers wrapped tightly around cock shaft:1.3), (hand gripping erect penis:1.3), "
            "(stroking dick:1.2), firm grip visible, "
            "erect cock entering frame from bottom (viewer's cock), "
            "her hand clearly in contact with shaft skin, "
            "looking up at camera while jerking cock, seductive smile, "
            "breasts visible, kneeling or sitting position, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "hand not touching cock, fingers apart, loose grip, hovering, "
            "side view, third person, man visible, full male body, "
            "clothes, bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_handjob_two_hands",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's POV, "
            "gorgeous nude {ethnicity} woman using both hands on cock, "
            "(both hands wrapped around shaft:1.3), (two-handed grip on cock:1.3), "
            "(double handjob:1.2), fingers interlaced around thick shaft, "
            "erect cock entering frame from bottom, "
            "both hands clearly touching and gripping cock, "
            "looking up at camera with lustful expression, "
            "breasts visible, kneeling position, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "hands not touching, one hand only, fingers apart, "
            "side view, third person, man visible, "
            "clothes, bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },

    # -----------------------------------------
    # POV BALL HANDLING - NEW SCENARIOS
    # Key patterns: "hand cupping balls", "fingers touching testicles"
    # -----------------------------------------
    {
        "name": "pov_cupping_balls",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view, "
            "beautiful nude {ethnicity} woman fondling balls, "
            "(hand cupping testicles:1.3), (palm holding balls:1.3), "
            "(fingers gently squeezing scrotum:1.2), "
            "erect cock visible above her hand, viewer's cock and balls in frame, "
            "her palm clearly in contact with ball sack, "
            "looking up at camera with teasing expression, "
            "nude, breasts visible, kneeling position, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "hand not touching balls, fingers apart, hovering, "
            "side view, third person, man visible, full male body, "
            "clothes, bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_licking_balls",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's POV, "
            "gorgeous nude {ethnicity} woman licking balls, "
            "(tongue on testicles:1.3), (tongue touching ball sack:1.3), "
            "(licking scrotum:1.2), tongue in direct contact with balls, "
            "erect cock visible above, viewer's cock and balls in frame, "
            "looking up at camera while licking balls, "
            "nude, breasts visible below, submissive expression, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "tongue not touching, licking cock instead, mouth closed, "
            "side view, third person, man visible, "
            "clothes, bad anatomy, cartoon, anime, blurry, soft penis"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_balls_in_mouth",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's point of view, "
            "beautiful nude {ethnicity} woman with balls in mouth, "
            "(testicle in mouth:1.3), (sucking on balls:1.3), "
            "(lips wrapped around ball:1.2), one or both balls inside mouth, "
            "erect cock resting on her face above, viewer's cock and balls, "
            "cheeks bulging slightly from ball in mouth, "
            "looking up at camera while sucking balls, "
            "nude, breasts visible, submissive expression, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "balls outside mouth, licking only, sucking cock instead, "
            "side view, third person, man visible, "
            "clothes, bad anatomy, cartoon, anime, blurry, soft penis"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },

    # -----------------------------------------
    # COMBINED ACTIONS - Hand on cock + licking/sucking
    # -----------------------------------------
    {
        "name": "pov_handjob_lick",
        "category": "pov_combo",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's POV, "
            "gorgeous nude {ethnicity} woman, "
            "(hand gripping cock shaft:1.3) while (tongue licking tip:1.3), "
            "(stroking and licking:1.2), handjob with oral tease, "
            "erect cock entering frame from bottom, "
            "fingers wrapped around shaft while tongue touches head, "
            "looking up at camera, multitasking expression, "
            "nude, breasts visible, kneeling, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "hand not touching, tongue not touching, mouth closed, "
            "side view, third person, man visible, "
            "clothes, bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },
    {
        "name": "pov_blowjob_balls_fondle",
        "category": "pov_combo",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's POV, "
            "beautiful nude {ethnicity} woman, "
            "(cock in mouth:1.3) while (hand cupping balls:1.3), "
            "(sucking dick and fondling testicles:1.2), "
            "lips wrapped around shaft, fingers touching balls simultaneously, "
            "erect cock entering frame from bottom, "
            "multitasking blowjob, looking up at camera, "
            "nude, breasts visible, kneeling position, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "cock outside mouth, hand not on balls, single action only, "
            "side view, third person, man visible, "
            "clothes, bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },

    # -----------------------------------------
    # POV TITJOB - IMPROVED WITH CONTACT
    # -----------------------------------------
    {
        "name": "pov_titjob_squeeze",
        "category": "pov_touch",
        "prompt": (
            "(POV shot:1.4), (first person perspective:1.3), "
            "explicit photograph from viewer's POV looking down, "
            "nude {ethnicity} woman giving titjob, "
            "(breasts pressed tightly around cock:1.3), (penis between tits:1.3), "
            "(titfuck:1.2), hands squeezing breasts together around shaft, "
            "cock entering frame from bottom (viewer's cock), "
            "cock clearly sandwiched between her breasts, skin contact visible, "
            "looking up at camera seductively, natural medium-large breasts, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "cock not between breasts, breasts apart, no contact, "
            "side view, third person, man visible, "
            "small breasts, flat chest, clothes, "
            "bad anatomy, cartoon, anime, blurry, soft penis, flaccid"
        ),
        "loras": [("airoticart_penis.safetensors", 0.85), ("polyhedron_skin.safetensors", 0.4)],
        "uses_penis_lora": True
    },

    # -----------------------------------------
    # POST-ACT CUM SHOTS - Same as V2
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
            "messy facial cumshot result, no male visible in frame, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis visible, cock, "
            "clean face, no cum, clothes, "
            "bad anatomy, deformed, ugly, cartoon, anime, blurry"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)],
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
            "no male visible in frame, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis visible, cock, "
            "clean breasts, no cum, clothes, "
            "bad anatomy, cartoon, anime, blurry"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)],
        "uses_penis_lora": False
    },

    # -----------------------------------------
    # SOLO POSES
    # -----------------------------------------
    {
        "name": "doggy_waiting",
        "category": "solo_pose",
        "prompt": (
            "(single woman:1.4), (one person only:1.3), "
            "explicit photograph of beautiful nude {ethnicity} woman, solo subject, "
            "on all fours doggy style position on bed, ass up face down, "
            "looking back over shoulder at camera seductively, "
            "pussy visible from behind, arched back, waiting pose, "
            "no other person in frame, on white silk sheets, soft lighting, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis, cock, second person, "
            "clothes, standing, lying flat, "
            "bad anatomy, cartoon, anime, blurry"
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
            "on white silk sheets, soft lighting, "
            "photorealistic, sharp focus, 8k uhd"
        ),
        "negative": (
            "multiple people, man, male, penis, second person, "
            "clothes, legs closed, standing, "
            "bad anatomy, cartoon, anime, blurry"
        ),
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)],
        "uses_penis_lora": False
    },
]

# Resolutions
RESOLUTIONS = [
    (768, 1152),
    (768, 1280),
    (832, 1216),
]


def generate_image(idx: int, ethnicity: str, scenario: dict, resolution: tuple, seed: int):
    """Generate a single image."""
    prompt = scenario["prompt"].format(ethnicity=ethnicity)
    negative = scenario["negative"]
    scenario_name = scenario["name"]
    loras = scenario.get("loras", [])

    width, height = resolution

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eth_short = ethnicity.replace(" ", "_")[:10]

    output_name = f"{timestamp}_explicit_v3_{idx:03d}_{eth_short}_{scenario_name}"
    output_path = f"/tmp/{output_name}.png"

    # Use higher steps (70) for better quality with explicit content
    # CFG 9.0 for stricter prompt adherence
    cmd = [
        "python3", "generate.py",
        "--workflow", "workflows/majicmix-realistic.json",
        "--prompt", prompt,
        "--negative-prompt", negative,
        "--steps", "70",
        "--cfg", "9.0",
        "--seed", str(seed),
        "--width", str(width),
        "--height", str(height),
        "--output", output_path,
    ]

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
        print("  [TIMEOUT]")
        return False, None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False, None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch explicit generation V3 - improved contact")
    parser.add_argument("--count", type=int, default=50, help="Number of images")
    parser.add_argument("--start", type=int, default=1, help="Starting index")
    parser.add_argument("--dry-run", action="store_true", help="Print without executing")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--list", action="store_true", help="List scenarios")
    args = parser.parse_args()

    if args.list:
        print("V3 Scenarios (with improved contact descriptions):")
        print("-" * 70)
        for s in SCENARIOS:
            print(f"  {s['name']:25s} [{s['category']:12s}] penis_lora={s['uses_penis_lora']}")
        print("-" * 70)
        print("Categories: solo, pov_oral, pov_touch, pov_combo, cum, solo_pose")
        return

    print("=" * 70)
    print("Explicit NSFW Batch Generation - V3 (Improved Contact Prompts)")
    print("=" * 70)
    print("Improvements over V2:")
    print("  - Explicit contact emphasis: (lips wrapped around cock:1.3)")
    print("  - Ball handling scenarios added")
    print("  - Combo actions (handjob + licking)")
    print("  - Negative prompts for NON-contact to prevent hovering")
    print("=" * 70)

    scenarios = SCENARIOS
    if args.category:
        scenarios = [s for s in SCENARIOS if s['category'] == args.category]
        print(f"Filtered to: {args.category} ({len(scenarios)} scenarios)")

    queue = []
    idx = args.start

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

    print("\n" + "=" * 70)
    print(f"Success: {success}, Failed: {failed}")

    if urls:
        print("\nLast 10 URLs:")
        for url in urls[-10:]:
            print(f"  {url}")


if __name__ == "__main__":
    main()
