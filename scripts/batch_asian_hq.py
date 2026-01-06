#!/usr/bin/env python3
"""
Ultra-HQ Asian blowjob batch generation.
5 highly detailed scenarios with maximum quality settings.
"""

import subprocess
import sys
from pathlib import Path

# Base quality tags for Pony Realism
QUALITY_POSITIVE = "score_9, score_8_up, score_7_up, rating_explicit, masterpiece, best quality, ultra detailed, 8k uhd, high resolution, photorealistic, hyperrealistic, raw photo, film grain"
QUALITY_NEGATIVE = "score_6, score_5, score_4, worst quality, low quality, normal quality, jpeg artifacts, blurry, bad anatomy, bad hands, deformed, ugly, watermark, signature, text, anime, cartoon, 3d render, cgi, illustration, painting, drawing"

# 5 Ultra-detailed scenarios
SCENARIOS = [
    {
        "name": "pov_blowjob_eye_contact",
        "prompt": f"{QUALITY_POSITIVE}, photo, 1girl, 1boy, asian woman, beautiful face, almond eyes, black hair, looking at viewer, pov, blowjob, oral sex, sucking cock, (big white cock:1.3), (penis in mouth:1.3), holding penis with hand, hand on shaft, eye contact, intimate moment, bedroom lighting, soft shadows, shallow depth of field, close up portrait, upper body, (realistic skin texture:1.2), (detailed face:1.3), lipstick slightly smudged, wet lips, saliva",
        "negative": f"{QUALITY_NEGATIVE}, (bad penis:1.3), (deformed cock:1.3), multiple penises, extra limbs",
        "loras": [("zy_AmateurStyle_v2.safetensors", 0.85)],
        "steps": 60,
        "cfg": 6.5,
    },
    {
        "name": "side_profile_balls_visible",
        "prompt": f"{QUALITY_POSITIVE}, photo, 1girl, 1boy, asian woman, beautiful korean woman, delicate features, porcelain skin, black silky hair, side view, profile shot, blowjob, oral sex, (big white cock:1.3), (cock in mouth:1.3), (testicles visible:1.2), (balls dangling:1.2), one hand cupping balls, sensual expression, closed eyes, enjoying, bedroom, natural lighting from window, golden hour light, intimate atmosphere, (realistic anatomy:1.2), (detailed skin pores:1.1), subtle makeup",
        "negative": f"{QUALITY_NEGATIVE}, (bad penis:1.3), (deformed testicles:1.3), front view, looking at camera",
        "loras": [("zy_AmateurStyle_v2.safetensors", 0.8)],
        "steps": 65,
        "cfg": 6.0,
    },
    {
        "name": "facial_cumshot",
        "prompt": f"{QUALITY_POSITIVE}, photo, 1girl, 1boy, asian woman, japanese woman, cute face, (facial cumshot:1.4), (cum on face:1.4), (realistic cum:1.3), cum dripping, cum on cheeks, cum on lips, cum on chin, eyes closed, mouth open, tongue out, (big white cock:1.2), hand holding cock near face, post orgasm, messy, wet face, glistening, satisfied expression, bedroom setting, soft diffused lighting, (photorealistic skin:1.2), (detailed pores:1.1), natural beauty",
        "negative": f"{QUALITY_NEGATIVE}, (fake cum:1.2), (bad cum:1.2), clean face, no cum, cartoon cum",
        "loras": [("zy_AmateurStyle_v2.safetensors", 0.75), ("realcumv6.55.safetensors", 0.8)],
        "steps": 60,
        "cfg": 7.0,
    },
    {
        "name": "two_hands_licking_tip",
        "prompt": f"{QUALITY_POSITIVE}, photo, 1girl, 1boy, asian woman, chinese woman, elegant features, long black hair, both hands wrapped around shaft, (two hands on cock:1.3), (stroking penis:1.2), (licking tip:1.3), tongue on glans, teasing, sensual, looking up at viewer, seductive eyes, playful expression, (big white erect cock:1.3), (veiny shaft:1.2), precum on tip, bedroom, dim romantic lighting, candles, intimate setting, (hyperrealistic:1.2), (detailed hands:1.3), manicured nails, red nail polish",
        "negative": f"{QUALITY_NEGATIVE}, (bad hands:1.4), (wrong fingers:1.3), (deformed hands:1.3), extra fingers, missing fingers, (bad penis:1.2)",
        "loras": [("zy_AmateurStyle_v2.safetensors", 0.9)],
        "steps": 70,
        "cfg": 6.5,
    },
    {
        "name": "deepthroat_sloppy",
        "prompt": f"{QUALITY_POSITIVE}, photo, 1girl, 1boy, asian woman, thai woman, exotic beauty, tan skin, (deepthroat:1.4), (cock deep in mouth:1.3), (sloppy blowjob:1.3), saliva strings, drool, messy, tears in eyes, mascara running slightly, (big white cock:1.2), hand on thigh, submission, intense, passionate, hotel room, harsh overhead lighting, gritty realistic, documentary style, (raw unfiltered:1.2), (realistic messy:1.2), smeared lipstick, disheveled hair",
        "negative": f"{QUALITY_NEGATIVE}, clean, pristine, perfect makeup, (bad anatomy:1.3), cartoon",
        "loras": [("zy_AmateurStyle_v2.safetensors", 0.85)],
        "steps": 65,
        "cfg": 6.0,
    },
]


def run_generation(scenario: dict, index: int) -> bool:
    """Run a single generation with given scenario."""
    name = scenario["name"]
    prompt = scenario["prompt"]
    negative = scenario["negative"]
    loras = scenario["loras"]
    steps = scenario["steps"]
    cfg = scenario["cfg"]
    
    output_name = f"asian_hq_{index:03d}_{name}.png"
    
    print(f"\n{'='*60}")
    print(f"[{index}/5] Generating: {name}")
    print(f"Steps: {steps}, CFG: {cfg}")
    print(f"LoRAs: {', '.join(f'{l[0]} @ {l[1]}' for l in loras)}")
    print(f"{'='*60}")
    
    # Build command
    cmd = [
        "python3", "generate.py",
        "--workflow", "workflows/pony-realism.json",
        "--prompt", prompt,
        "--negative-prompt", negative,
        "--steps", str(steps),
        "--cfg", str(cfg),
        "--output", f"/tmp/{output_name}",
    ]
    
    # Add each LoRA as separate flag
    for lora_name, lora_strength in loras:
        cmd.extend(["--lora", f"{lora_name}:{lora_strength}"])
    
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for high-quality
        )
        
        if result.returncode == 0:
            print(f"[OK] Generated: {output_name}")
            # Extract URL from output
            for line in result.stdout.split('\n'):
                if 'http://' in line and 'comfy-gen' in line:
                    print(f"    URL: {line.strip()}")
            return True
        else:
            print(f"[ERROR] Failed: {name}")
            print(f"    stderr: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Timeout: {name}")
        return False
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False


def main():
    start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    print(f"Ultra-HQ Asian Generation")
    print(f"Starting from scenario {start_idx}, generating {count} images")
    print(f"Using Pony Realism V2.2 + Amateur/Real Cum LoRAs")
    print(f"Max quality settings: 60-70 steps, detailed prompts")
    
    success = 0
    failed = 0
    
    for i in range(count):
        scenario_idx = (start_idx - 1 + i) % len(SCENARIOS)
        scenario = SCENARIOS[scenario_idx]
        
        if run_generation(scenario, start_idx + i):
            success += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {success} succeeded, {failed} failed")
    print(f"View at: http://192.168.1.215:9000/comfy-gen/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
