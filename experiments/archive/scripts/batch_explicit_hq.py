#!/usr/bin/env python3
"""
Batch generation of 100 explicit NSFW images - HIGH QUALITY VERSION
Higher resolution, better LoRAs for realism and explicit content.
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

# Scenario templates - varied explicit content with better prompts
SCENARIOS = [
    # Solo nude - basic
    {
        "name": "nude_standing",
        "prompt": "professional photograph of beautiful {ethnicity} woman, solo single person, completely naked nude, standing pose, natural medium breasts with visible nipples, flat toned stomach, shaved pussy visible, full body shot, looking at camera with seductive expression, soft studio lighting, sharp focus, photorealistic, high detail skin texture pores and imperfections, professional boudoir photography, 8k uhd",
        "negative": "clothes, clothed, dressed, bikini, underwear, bra, panties, multiple people, two people, duplicate, bad anatomy, deformed, ugly, blurry, low quality, cartoon, anime, painting, illustration, cgi",
        "loras": [("realora_skin.safetensors", 0.4), ("more_details.safetensors", 0.3)]
    },
    {
        "name": "nude_lying",
        "prompt": "professional photograph of gorgeous {ethnicity} woman, solo single person, fully nude naked, lying on white silk bed sheets, natural breasts exposed with erect nipples, legs slightly spread showing pussy, sensual relaxed pose, luxury bedroom setting, soft window light, photorealistic skin detail with pores and subtle imperfections, intimate boudoir photography style, 8k uhd sharp focus",
        "negative": "clothes, clothed, dressed, underwear, multiple people, duplicate, bad anatomy, deformed, ugly, blurry, cartoon, anime, standing, painting, cgi",
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)]
    },
    # With male - oral with penis LoRA
    {
        "name": "oral_kneeling",
        "prompt": "professional explicit photograph of beautiful {ethnicity} woman kneeling, nude naked, giving blowjob to large erect penis cock, dick in her mouth, sucking cock, man standing, her hands on his thighs, looking up at camera while sucking, natural breasts visible, explicit oral sex, photorealistic, high detail, sharp focus, 8k uhd",
        "negative": "clothes, dressed, bad anatomy, deformed face, ugly, blurry, cartoon, anime, multiple women, extra limbs, soft penis, flaccid",
        "loras": [("airoticart_penis.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)]
    },
    {
        "name": "oral_pov",
        "prompt": "POV blowjob first person view, beautiful {ethnicity} woman sucking large erect cock from viewer perspective, erect penis in her mouth, looking up at camera with dick between her lips, nude naked, her breasts visible below, explicit oral sex pov, photorealistic sharp focus, 8k uhd",
        "negative": "side view, third person, clothes, bad anatomy, cartoon, anime, blurry, multiple women, soft penis, flaccid, deformed",
        "loras": [("erect_penis_epoch_80.safetensors", 0.4), ("realora_skin.safetensors", 0.4)]
    },
    {
        "name": "deepthroat",
        "prompt": "explicit photograph of gorgeous nude {ethnicity} woman deepthroating large erect cock, penis deep in throat, mouth stretched around dick, slobber and drool, man standing, she is on knees, tears in eyes from deepthroat, explicit oral sex, photorealistic, sharp focus, 8k uhd",
        "negative": "clothes, bad anatomy, cartoon, anime, blurry, soft penis, deformed, multiple women",
        "loras": [("airoticart_penis.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)]
    },
    # Facial / cum
    {
        "name": "facial_cum",
        "prompt": "explicit photograph of beautiful {ethnicity} woman face covered in thick white cum semen, cum dripping from chin and cheeks, mouth open tongue out with cum, freshly cummed on facial, nude with breasts visible, messy facial cumshot result, kneeling pose, satisfied slutty expression, photorealistic, sharp focus, 8k uhd",
        "negative": "clean face, no cum, clothes, bad anatomy, deformed, ugly, cartoon, anime, blurry, dry cum",
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)]
    },
    {
        "name": "cum_mouth_open",
        "prompt": "explicit photograph of gorgeous {ethnicity} woman with cum in open mouth, thick white semen on lips and tongue, just received oral cumshot, swallowing cum, nude kneeling, breasts visible, looking at camera with cum dripping from mouth, photorealistic, sharp focus, 8k uhd",
        "negative": "clean, no cum, closed mouth, clothes, bad anatomy, cartoon, anime, blurry",
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)]
    },
    {
        "name": "cum_tits",
        "prompt": "explicit photograph of stunning nude {ethnicity} woman with thick white cum on her breasts, semen dripping between tits, cum covered chest, looking down at her messy breasts, satisfied smile, freshly cummed on, explicit cumshot result, photorealistic, sharp focus, 8k uhd",
        "negative": "clean, no cum, clothes, bad anatomy, deformed, cartoon, anime, blurry, dry",
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)]
    },
    # Positions with cock
    {
        "name": "titjob",
        "prompt": "explicit POV titjob photograph, nude {ethnicity} woman pressing her natural breasts around large erect cock penis, dick between her tits, looking up at camera seductively while giving titfuck, first person view, photorealistic, sharp focus, 8k uhd",
        "negative": "side view, clothes, bad anatomy, cartoon, anime, small breasts, blurry, soft penis, flaccid",
        "loras": [("airoticart_penis.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)]
    },
    {
        "name": "doggy_position",
        "prompt": "explicit photograph of beautiful nude {ethnicity} woman on all fours doggy style position, ass up face down on bed, looking back over shoulder at camera seductively, pussy visible from behind, arched back, waiting to be fucked pose, photorealistic, sharp focus, 8k uhd",
        "negative": "clothes, standing, lying flat, bad anatomy, cartoon, anime, blurry, multiple women, deformed",
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.3)]
    },
    {
        "name": "spread_pussy",
        "prompt": "explicit photograph of gorgeous nude {ethnicity} woman lying on back, legs spread wide open showing pink wet pussy, hands spreading pussy lips apart, natural breasts, inviting pose, on white silk sheets, soft lighting, explicit, photorealistic, sharp focus, 8k uhd",
        "negative": "clothes, legs closed, standing, bad anatomy, cartoon, anime, blurry, deformed",
        "loras": [("polyhedron_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)]
    },
    # Breast focus (emulating the good breast shot)
    {
        "name": "breast_closeup",
        "prompt": "professional photograph close up of beautiful {ethnicity} woman perfect natural breasts, medium size round perky tits with small erect nipples, smooth realistic skin texture with pores, hands cupping breasts, topless, soft natural lighting, photorealistic skin detail, sharp focus, 8k uhd",
        "negative": "full body, face focus, clothes, bra, bad anatomy, deformed nipples, cartoon, anime, blurry, fake looking, implants",
        "loras": [("realora_skin.safetensors", 0.5), ("more_details.safetensors", 0.4)]
    },
    {
        "name": "handjob",
        "prompt": "explicit POV photograph of beautiful nude {ethnicity} woman giving handjob, her hand wrapped around large erect cock penis, stroking dick, looking up at camera seductively, breasts visible, first person view handjob, photorealistic, sharp focus, 8k uhd",
        "negative": "side view, clothes, bad anatomy, cartoon, anime, blurry, soft penis, flaccid, deformed",
        "loras": [("erect_penis_epoch_80.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)]
    },
    {
        "name": "licking_cock",
        "prompt": "explicit photograph of gorgeous {ethnicity} woman licking large erect cock, tongue out licking shaft of penis, looking up at camera while licking dick, nude naked, seductive expression, oral foreplay, photorealistic, sharp focus, 8k uhd",
        "negative": "clothes, bad anatomy, cartoon, anime, blurry, soft penis, flaccid, deformed, multiple women",
        "loras": [("airoticart_penis.safetensors", 0.5), ("realora_skin.safetensors", 0.4)]
    }
]

# Higher resolution options (width, height) - portrait orientations for full body
RESOLUTIONS = [
    (768, 1152),   # HD portrait
    (768, 1280),   # Tall portrait
    (832, 1216),   # Wide-ish portrait
    (896, 1152),   # Wider portrait
]

def generate_image(idx: int, ethnicity: str, scenario: dict, resolution: tuple, seed: int):
    """Generate a single image."""
    prompt = scenario["prompt"].format(ethnicity=ethnicity)
    negative = scenario["negative"]
    scenario_name = scenario["name"]
    loras = scenario.get("loras", [])

    width, height = resolution

    # Build filename
    eth_short = ethnicity.replace(" ", "_")[:10]

    output_name = f"explicit_hq_{idx:03d}_{eth_short}_{scenario_name}"
    output_path = f"/tmp/{output_name}.png"

    # Build command
    cmd = [
        "python3", "generate.py",
        "--workflow", "workflows/majicmix-realistic.json",
        "--prompt", prompt,
        "--negative-prompt", negative,
        "--steps", "60",      # More steps for quality
        "--cfg", "9",         # Higher CFG for prompt adherence
        "--seed", str(seed),
        "--width", str(width),
        "--height", str(height),
        "--output", output_path,
    ]

    # Add LoRAs from scenario
    for lora_file, strength in loras:
        cmd.extend(["--lora", f"{lora_file}:{strength}"])

    print(f"\n[{idx:03d}/100] {ethnicity} - {scenario_name}")
    print(f"  Resolution: {width}x{height}, Seed: {seed}")
    print(f"  LoRAs: {loras}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # Longer timeout for higher res
            cwd="/Users/jrjenkinsiv/Development/comfy-gen"
        )

        if result.returncode == 0:
            print("  [OK] Generated successfully")
            return True
        else:
            print(f"  [ERROR] {result.stderr[-300:] if result.stderr else 'Unknown error'}")
            return False

    except subprocess.TimeoutExpired:
        print("  [TIMEOUT] Generation took too long")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    print("=" * 60)
    print("Explicit NSFW Batch Generation - HIGH QUALITY")
    print("Higher resolution, better LoRAs for realism")
    print("=" * 60)

    total = 100
    success = 0
    failed = 0

    for i in range(1, total + 1):
        # Random selections
        ethnicity = random.choice(ETHNICITIES)
        scenario = random.choice(SCENARIOS)
        resolution = random.choice(RESOLUTIONS)
        seed = random.randint(1, 999999999)

        if generate_image(i, ethnicity, scenario, resolution, seed):
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
