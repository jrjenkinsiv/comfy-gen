#!/usr/bin/env python3
"""
Batch character generation for youngboh game.
Tests variations of poses, expressions, and angles for character selection.
"""

import json
import subprocess
import sys
from pathlib import Path

# Paths
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"
OUTPUT_DIR = Path("/tmp/youngboh_batch")
OUTPUT_DIR.mkdir(exist_ok=True)

# Base character description
BASE_CHARACTER = "The Boondocks anime style, African American Black teenage boy, dark brown skin tone, West African features, full lips, broad nose, African facial structure, 18 years old young man, youthful face, short chubby build, small natural afro hairstyle, large expressive brown eyes, slightly protruding ears, deep brown mocha complexion, wearing red and white Air Jordan sneakers, white t-shirt, baggy blue jeans with rips at knees"

# Variations to test
POSES = [
    "standing straight, arms at sides, neutral stance",
    "standing with hands in pockets, casual stance",
    "walking forward, mid-step",
    "leaning against wall, relaxed pose",
    "sitting on chair, legs crossed",
    "standing with arms crossed, defensive posture",
    "standing with one hand scratching head, confused gesture",
    "standing with hand waving, friendly gesture",
    "running pose, action shot",
    "crouching down, dynamic pose",
]

EXPRESSIONS = [
    "nervous awkward expression",
    "confident smirk",
    "worried anxious face",
    "angry determined expression",
    "happy smiling face",
    "sad disappointed look",
    "surprised shocked expression",
    "tired exhausted face",
    "neutral calm expression",
    "embarrassed blushing face",
]

ANGLES = [
    "front view, facing camera directly",
    "3/4 view, slightly angled",
    "side profile view",
    "slight low angle looking up",
    "slight high angle looking down",
]

# Body language variations
BODY_LANGUAGE = [
    "confident body language, chest out",
    "timid body language, shoulders hunched",
    "relaxed body language, loose posture",
    "tense body language, rigid stance",
]

# Additional style modifiers
LORAS = [
    None,  # No LoRA
    "The_BoondocksILL.safetensors:0.6",
    "Boondocks_style_and_characters.safetensors:0.5",
    "NarutoSS.safetensors:0.4",
]

NEGATIVE_PROMPT = "thin lips, narrow nose, European features, Asian features, pale skin, light skin, white person, caucasian, realistic, photorealistic, 3d render, photography, blurry, distorted, bad anatomy, extra limbs, watermark, text, child, kid, aged, wrinkled, mature face, weathered, old looking, middle-aged, 30s, 40s, gaunt, hollow cheeks, female, woman, girl, feminine, breasts, makeup, jewelry, stickers, patches, badges"

def generate_variations():
    """Generate a grid of character variations."""
    
    results = []
    test_id = 1
    
    # Generate combinations
    for pose in POSES:
        for expression in EXPRESSIONS[:5]:  # Limit expressions to 5 per pose
            for angle in ANGLES[:3]:  # Limit angles to 3
                for lora in LORAS[:2]:  # Test with/without LoRA
                    
                    # Build prompt
                    prompt = f"{BASE_CHARACTER}, {pose}, {expression}, {angle}, full body character design, clean anime lines, cel animation style, white background"
                    
                    # Build command
                    output_file = OUTPUT_DIR / f"youngboh_{test_id:03d}.png"
                    
                    cmd = [
                        sys.executable, str(GENERATE_PY),
                        "--workflow", "workflows/illustrious-anime.json",
                        "--prompt", prompt,
                        "--negative-prompt", NEGATIVE_PROMPT,
                        "--steps", "40",  # Faster generation
                        "--cfg", "7.5",
                        "--output", str(output_file),
                    ]
                    
                    if lora:
                        cmd.extend(["--lora", lora])
                    
                    print(f"\n{'='*60}")
                    print(f"[{test_id}/50] Generating variation...")
                    print(f"Pose: {pose}")
                    print(f"Expression: {expression}")
                    print(f"Angle: {angle}")
                    print(f"LoRA: {lora or 'None'}")
                    print(f"{'='*60}")
                    
                    # Run generation
                    try:
                        result = subprocess.run(
                            cmd,
                            cwd=str(COMFY_GEN_DIR),
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        
                        # Extract image URL from output
                        image_url = None
                        for line in result.stdout.split('\n'):
                            if 'http://192.168.1.215:9000/comfy-gen/' in line:
                                image_url = line.split('http://192.168.1.215:9000/comfy-gen/')[1].strip()
                                image_url = f"http://192.168.1.215:9000/comfy-gen/{image_url}"
                                break
                        
                        # Extract score
                        score = None
                        for line in result.stdout.split('\n'):
                            if 'Score:' in line:
                                score = float(line.split('Score:')[1].strip())
                                break
                        
                        status = "success" if result.returncode == 0 else "failed"
                        
                        results.append({
                            "id": test_id,
                            "status": status,
                            "pose": pose,
                            "expression": expression,
                            "angle": angle,
                            "lora": lora,
                            "url": image_url,
                            "score": score,
                            "returncode": result.returncode,
                        })
                        
                        if image_url:
                            print(f"[OK] Generated: {image_url}")
                            print(f"[OK] Score: {score}")
                        else:
                            print(f"[ERROR] Failed to generate")
                            print(result.stderr)
                        
                    except subprocess.TimeoutExpired:
                        print(f"[ERROR] Timeout on test {test_id}")
                        results.append({
                            "id": test_id,
                            "status": "timeout",
                            "pose": pose,
                            "expression": expression,
                            "angle": angle,
                            "lora": lora,
                        })
                    except Exception as e:
                        print(f"[ERROR] Exception: {e}")
                        results.append({
                            "id": test_id,
                            "status": "error",
                            "pose": pose,
                            "expression": expression,
                            "angle": angle,
                            "lora": lora,
                            "error": str(e),
                        })
                    
                    test_id += 1
                    
                    # Stop after 50 tests
                    if test_id > 50:
                        break
                
                if test_id > 50:
                    break
            if test_id > 50:
                break
        if test_id > 50:
            break
    
    # Save results
    results_file = COMFY_GEN_DIR / "youngboh_batch_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Batch generation complete!")
    print(f"Results saved to: {results_file}")
    print(f"Total successful: {len([r for r in results if r['status'] == 'success'])}/{len(results)}")
    print(f"{'='*60}")
    
    # Print all image URLs for easy viewing
    print("\nAll generated images:")
    for r in results:
        if r['status'] == 'success' and r.get('url'):
            print(f"[{r['id']:03d}] {r['url']} (score: {r.get('score', 'N/A')})")

if __name__ == "__main__":
    generate_variations()
