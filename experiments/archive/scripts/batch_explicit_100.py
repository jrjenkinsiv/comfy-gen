#!/usr/bin/env python3
"""
Batch generation of 100 explicit NSFW images.
Categories: Asian + South Asian/Middle Eastern women
Scenarios: nude poses, oral, facials, etc.
"""

import random
import subprocess
import sys
import time

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Ethnicities - expanded to include browner skin tones
ETHNICITIES = [
    # East Asian
    "japanese", "korean", "chinese", "vietnamese", "thai", "filipino",
    "taiwanese", "singaporean", "malaysian", "indonesian",
    # South Asian
    "indian", "pakistani", "bangladeshi", "sri lankan", "nepali",
    # Middle Eastern
    "persian", "arab", "jordanian", "lebanese", "turkish", "egyptian",
    # Mixed descriptors
    "south asian", "southeast asian", "middle eastern"
]

# Scenario templates - varied explicit content
SCENARIOS = [
    # Solo nude - basic
    {
        "name": "nude_standing",
        "prompt": "beautiful {ethnicity} woman, solo, completely naked nude, standing pose, natural medium breasts with visible nipples, flat stomach, shaved pussy visible, full body shot, looking at camera with seductive expression, soft natural lighting, photorealistic, high detail skin texture, professional photography",
        "negative": "clothes, clothed, dressed, bikini, underwear, bra, panties, multiple people, two people, duplicate, bad anatomy, deformed, ugly, blurry, low quality, cartoon, anime"
    },
    {
        "name": "nude_lying",
        "prompt": "gorgeous {ethnicity} woman, solo, fully nude naked, lying on white bed sheets, natural breasts exposed with erect nipples, legs slightly spread showing pussy, sensual relaxed pose, bedroom setting, soft window light, photorealistic skin detail, intimate boudoir photography style",
        "negative": "clothes, clothed, dressed, underwear, multiple people, duplicate, bad anatomy, deformed, ugly, blurry, cartoon, anime, standing"
    },
    {
        "name": "nude_kneeling",
        "prompt": "stunning {ethnicity} woman, solo, completely nude, kneeling pose on bed, perky natural breasts with visible nipples, smooth skin, shaved vulva visible, hands on thighs, looking up at camera submissively, soft lighting, photorealistic, professional erotic photography",
        "negative": "clothes, dressed, underwear, multiple people, duplicate, bad anatomy, deformed, standing, lying, cartoon, anime, blurry"
    },
    # With male - oral
    {
        "name": "oral_kneeling",
        "prompt": "beautiful {ethnicity} woman kneeling, nude, giving blowjob to erect penis, cock in mouth, sucking dick, man standing, her hands on his thighs, looking up at camera, natural breasts visible, explicit oral sex, photorealistic, high detail",
        "negative": "clothes, dressed, bad anatomy, deformed face, ugly, blurry, cartoon, anime, multiple women, extra limbs"
    },
    {
        "name": "oral_lying",
        "prompt": "gorgeous nude {ethnicity} woman lying on back, head tilted back off edge of bed, erect cock in her open mouth, deepthroat, man standing over her, her breasts exposed, explicit oral sex position, photorealistic detail",
        "negative": "clothes, bad anatomy, deformed, ugly, cartoon, anime, multiple women, blurry"
    },
    # Facial / cum
    {
        "name": "facial_cum",
        "prompt": "beautiful {ethnicity} woman face covered in cum, semen on face, cum dripping from chin, mouth open tongue out, freshly cummed on, nude with breasts visible, messy facial cumshot, satisfied expression, kneeling pose, explicit, photorealistic",
        "negative": "clean face, no cum, clothes, bad anatomy, deformed, ugly, cartoon, anime, blurry"
    },
    {
        "name": "cum_tits",
        "prompt": "stunning nude {ethnicity} woman with cum on her breasts, semen dripping between tits, cum covered chest, looking down at messy breasts, satisfied smile, freshly cummed on, explicit cumshot result, photorealistic",
        "negative": "clean, no cum, clothes, bad anatomy, deformed, cartoon, anime, blurry"
    },
    {
        "name": "cum_mouth",
        "prompt": "gorgeous {ethnicity} woman with cum in open mouth, semen on lips and tongue, swallowing cum, nude kneeling, breasts visible, just received oral cumshot, looking at camera, explicit, photorealistic",
        "negative": "clean, no cum, closed mouth, clothes, bad anatomy, cartoon, anime, blurry"
    },
    # POV angles
    {
        "name": "pov_oral",
        "prompt": "POV blowjob, beautiful {ethnicity} woman sucking cock from viewer perspective, erect penis in her mouth, looking up at camera with cock between lips, nude, her breasts visible below, first person view oral sex, photorealistic",
        "negative": "side view, third person, clothes, bad anatomy, cartoon, anime, blurry, multiple women"
    },
    {
        "name": "pov_tits",
        "prompt": "POV titjob, nude {ethnicity} woman pressing her natural breasts around erect cock, penis between tits, looking up at camera seductively, first person view, explicit, photorealistic",
        "negative": "side view, clothes, bad anatomy, cartoon, anime, small breasts, blurry"
    },
    # Positions
    {
        "name": "doggy_position",
        "prompt": "beautiful nude {ethnicity} woman on all fours doggy style position, ass up face down, looking back over shoulder at camera, pussy visible from behind, waiting pose, on bed, arched back, photorealistic, explicit",
        "negative": "clothes, standing, lying flat, bad anatomy, cartoon, anime, blurry, multiple women"
    },
    {
        "name": "spread_legs",
        "prompt": "gorgeous nude {ethnicity} woman lying on back, legs spread wide open showing pink pussy, hands holding thighs apart, natural breasts, inviting pose, on white sheets, soft lighting, explicit, photorealistic",
        "negative": "clothes, legs closed, standing, bad anatomy, cartoon, anime, blurry"
    },
    # Breast focus (emulating the good breast shot)
    {
        "name": "breast_focus",
        "prompt": "beautiful {ethnicity} woman, close up of perfect natural breasts, medium size round perky tits with small brown nipples, smooth skin texture, hands cupping breasts, topless, soft natural lighting, photorealistic skin detail, professional photography",
        "negative": "full body, face focus, clothes, bra, bad anatomy, deformed nipples, cartoon, anime, blurry, fake looking"
    },
    {
        "name": "breast_squeeze",
        "prompt": "stunning nude {ethnicity} woman squeezing her natural breasts together, creating cleavage, perky nipples, hands pressing tits, looking at camera seductively, topless upper body shot, soft lighting, photorealistic",
        "negative": "clothes, bra, bad anatomy, cartoon, anime, blurry, full body"
    }
]

# LoRA configurations based on what worked
LORA_CONFIGS = [
    [("polyhedron_skin.safetensors", 0.5)],
    [("polyhedron_skin.safetensors", 0.6)],
    [("polyhedron_skin.safetensors", 0.4), ("add_detail.safetensors", 0.3)],
    [("polyhedron_skin.safetensors", 0.5), ("add_detail.safetensors", 0.2)],
    None,  # No LoRA sometimes
]

# Resolution options (width, height)
RESOLUTIONS = [
    (512, 768),   # Portrait
    (576, 768),   # Slightly wider portrait
    (512, 704),   # Standard portrait
]

def generate_image(idx: int, ethnicity: str, scenario: dict, lora_config, resolution: tuple, seed: int):
    """Generate a single image."""
    prompt = scenario["prompt"].format(ethnicity=ethnicity)
    negative = scenario["negative"]
    scenario_name = scenario["name"]

    width, height = resolution

    # Build filename
    eth_short = ethnicity.replace(" ", "_")[:10]
    lora_name = "none"
    if lora_config:
        lora_name = lora_config[0][0].replace(".safetensors", "")[:12]

    output_name = f"explicit_{idx:03d}_{eth_short}_{scenario_name}_{lora_name}"
    output_path = f"/tmp/{output_name}.png"

    # Build command
    cmd = [
        "python3", "generate.py",
        "--workflow", "workflows/majicmix-realistic.json",
        "--prompt", prompt,
        "--negative-prompt", negative,
        "--steps", "50",
        "--cfg", "8",
        "--seed", str(seed),
        "--width", str(width),
        "--height", str(height),
        "--output", output_path,
    ]

    # Add LoRAs if configured
    if lora_config:
        for lora_file, strength in lora_config:
            cmd.extend(["--lora", f"{lora_file}:{strength}"])

    print(f"\n[{idx:03d}/100] {ethnicity} - {scenario_name}")
    print(f"  Resolution: {resolution}, Seed: {seed}")
    if lora_config:
        print(f"  LoRAs: {lora_config}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd="/Users/jrjenkinsiv/Development/comfy-gen"
        )

        if result.returncode == 0:
            print("  [OK] Generated successfully")
            return True
        else:
            print(f"  [ERROR] {result.stderr[-200:] if result.stderr else 'Unknown error'}")
            return False

    except subprocess.TimeoutExpired:
        print("  [TIMEOUT] Generation took too long")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    print("=" * 60)
    print("Explicit NSFW Batch Generation - 100 Images")
    print("=" * 60)

    total = 100
    success = 0
    failed = 0

    for i in range(1, total + 1):
        # Random selections
        ethnicity = random.choice(ETHNICITIES)
        scenario = random.choice(SCENARIOS)
        lora_config = random.choice(LORA_CONFIGS)
        resolution = random.choice(RESOLUTIONS)
        seed = random.randint(1, 999999999)

        if generate_image(i, ethnicity, scenario, lora_config, resolution, seed):
            success += 1
        else:
            failed += 1

        # Small delay between generations
        time.sleep(2)

    print("\n" + "=" * 60)
    print(f"COMPLETE: {success} successful, {failed} failed out of {total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
