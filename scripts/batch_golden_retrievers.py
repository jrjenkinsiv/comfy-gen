#!/usr/bin/env python3
"""
Batch Golden Retriever Generation Experiment
- 20 images with varied parameters
- Different scenarios worldwide
- Various steps, CFG, resolutions
- Upscaled and non-upscaled
"""

import subprocess
import json
import time
from datetime import datetime
import random

# Golden retriever scenarios from around the world
SCENARIOS = [
    # Nature/Outdoor
    {
        "name": "beach_california",
        "prompt": "golden retriever dog running on sandy beach at sunset, Pacific Ocean waves, California coastline, golden hour light, wet fur glistening, joyful expression, action shot, professional pet photography",
        "negative": "blurry, distorted, bad anatomy, extra legs, watermark, text",
    },
    {
        "name": "alps_switzerland",
        "prompt": "golden retriever dog sitting in alpine meadow, Swiss Alps mountains in background, wildflowers, clear blue sky, majestic landscape, fluffy golden coat, loyal expression, nature photography",
        "negative": "blurry, distorted, bad anatomy, watermark, text, people",
    },
    {
        "name": "autumn_vermont",
        "prompt": "golden retriever puppy playing in pile of autumn leaves, New England fall foliage, vibrant red orange yellow colors, playful pose, cute expression, soft natural lighting, pet photography",
        "negative": "blurry, distorted, bad anatomy, extra limbs, watermark",
    },
    {
        "name": "cherry_blossom_japan",
        "prompt": "golden retriever sitting under cherry blossom tree in full bloom, Japanese garden, sakura petals falling, serene peaceful scene, spring in Kyoto, beautiful golden fur, contemplative pose",
        "negative": "blurry, distorted, bad anatomy, watermark, text",
    },
    {
        "name": "lake_canada",
        "prompt": "golden retriever swimming in crystal clear Canadian lake, mountains reflected in water, wilderness, splashing water droplets, happy dog, summer adventure, outdoor photography",
        "negative": "blurry, distorted, bad anatomy, watermark",
    },
    # Urban/City
    {
        "name": "central_park_nyc",
        "prompt": "golden retriever on leash walking through Central Park New York City, fall season, city skyline in background, fallen leaves on path, urban dog life, well-groomed coat, street photography",
        "negative": "blurry, distorted, bad anatomy, watermark, text",
    },
    {
        "name": "paris_cafe",
        "prompt": "golden retriever lying under outdoor cafe table in Paris, Eiffel Tower visible in distance, cobblestone street, French atmosphere, relaxed elegant dog, European city life",
        "negative": "blurry, distorted, bad anatomy, watermark, cartoon",
    },
    {
        "name": "london_park",
        "prompt": "golden retriever catching frisbee mid-air in Hyde Park London, Big Ben visible in background, green grass, athletic leap, action freeze frame, dynamic pet photography",
        "negative": "blurry, distorted, bad anatomy, extra legs, watermark",
    },
    # Home/Cozy
    {
        "name": "fireplace_cozy",
        "prompt": "golden retriever sleeping peacefully by stone fireplace, cozy cabin interior, warm amber light, soft blanket, winter evening, content expression, heartwarming scene, indoor photography",
        "negative": "blurry, distorted, bad anatomy, watermark",
    },
    {
        "name": "christmas_morning",
        "prompt": "golden retriever puppy with red bow sitting next to Christmas tree, presents, festive decorations, twinkling lights, excited expression, holiday portrait, warm family atmosphere",
        "negative": "blurry, distorted, bad anatomy, watermark, text",
    },
    {
        "name": "kitchen_cooking",
        "prompt": "golden retriever sitting attentively in modern kitchen watching owner cook, hoping for treats, curious expression, domestic scene, lifestyle photography, warm lighting",
        "negative": "blurry, distorted, bad anatomy, watermark",
    },
    # Adventure/Action
    {
        "name": "snow_alaska",
        "prompt": "golden retriever playing in deep fresh snow, Alaska wilderness, snow-covered pine trees, powder flying, exuberant joy, winter wonderland, action photography, frosty breath",
        "negative": "blurry, distorted, bad anatomy, watermark",
    },
    {
        "name": "hiking_colorado",
        "prompt": "golden retriever on mountain hiking trail, Rocky Mountains Colorado, panoramic vista, adventure dog with backpack, exploration, wilderness, epic landscape photography",
        "negative": "blurry, distorted, bad anatomy, watermark, text",
    },
    {
        "name": "surfing_australia",
        "prompt": "golden retriever standing on surfboard riding small wave, Australian beach, Bondi, action sports, wet fur, amazing balance, extreme pet photography, ocean spray",
        "negative": "blurry, distorted, bad anatomy, watermark",
    },
    # Portraits/Close-ups
    {
        "name": "studio_portrait",
        "prompt": "professional studio portrait of golden retriever, black background, dramatic lighting, piercing intelligent eyes, noble expression, show dog quality, award-winning pet photography",
        "negative": "blurry, distorted, bad anatomy, watermark, text",
    },
    {
        "name": "golden_hour_portrait",
        "prompt": "close-up portrait of golden retriever face at golden hour, backlit fur glowing, warm sunset colors, soulful brown eyes, soft focus background, emotional connection, fine art photography",
        "negative": "blurry, distorted, bad anatomy, watermark",
    },
    {
        "name": "puppy_closeup",
        "prompt": "extreme close-up of adorable golden retriever puppy face, big innocent eyes, wet black nose, fluffy fur, curious expression, shallow depth of field, heartmelting cuteness",
        "negative": "blurry, distorted, bad anatomy, watermark, adult dog",
    },
    # Unique/Creative
    {
        "name": "graduation_cap",
        "prompt": "golden retriever wearing graduation cap, proud expression, accomplishment, funny pet photo, celebration, clever dog, humorous portrait, sharp focus",
        "negative": "blurry, distorted, bad anatomy, watermark, text",
    },
    {
        "name": "rain_puddle",
        "prompt": "golden retriever splashing through rain puddle, rainy day, water droplets in air, joyful chaos, Seattle weather, wet happy dog, dynamic action shot, reflection",
        "negative": "blurry, distorted, bad anatomy, watermark",
    },
    {
        "name": "sunset_silhouette",
        "prompt": "golden retriever silhouette against dramatic sunset sky, beach, orange purple clouds, artistic composition, contemplative mood, fine art pet photography, cinematic",
        "negative": "blurry, distorted, watermark, text, face details visible",
    },
]

# Parameter variations
CONFIGS = [
    # Standard quality
    {"steps": 30, "cfg": 7.5, "width": 1024, "height": 1024, "upscale": False},
    {"steps": 30, "cfg": 7.0, "width": 1024, "height": 1024, "upscale": False},
    {"steps": 30, "cfg": 8.0, "width": 1024, "height": 1024, "upscale": False},
    # High quality
    {"steps": 50, "cfg": 7.5, "width": 1024, "height": 1024, "upscale": False},
    {"steps": 50, "cfg": 8.0, "width": 1024, "height": 1024, "upscale": False},
    # Different aspect ratios
    {"steps": 35, "cfg": 7.5, "width": 1024, "height": 768, "upscale": False},  # Landscape
    {"steps": 35, "cfg": 7.5, "width": 768, "height": 1024, "upscale": False},  # Portrait
    {"steps": 35, "cfg": 7.5, "width": 1280, "height": 720, "upscale": False},  # Wide
    # Upscaled versions
    {"steps": 30, "cfg": 7.5, "width": 1024, "height": 1024, "upscale": True},
    {"steps": 40, "cfg": 7.5, "width": 1024, "height": 1024, "upscale": True},
]


def generate_image(scenario: dict, config: dict, index: int) -> dict:
    """Generate a single image with given scenario and config."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"golden_{scenario['name']}_{index}_{timestamp}"
    output_path = f"/tmp/{filename}.png"
    
    cmd = [
        "python3", "generate.py",
        "--workflow", "workflows/flux-dev.json",
        "--prompt", scenario["prompt"],
        "--negative-prompt", scenario["negative"],
        "--steps", str(config["steps"]),
        "--cfg", str(config["cfg"]),
        "--output", output_path,
    ]
    
    # Add resolution if workflow supports it
    # Note: Flux-dev workflow may need modification for custom resolutions
    
    print(f"\n[{index}/20] {scenario['name']}")
    print(f"  Steps: {config['steps']}, CFG: {config['cfg']}, Upscale: {config['upscale']}")
    print(f"  Prompt: {scenario['prompt'][:60]}...")
    
    start = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
            cwd="/Users/jrjenkinsiv/Development/comfy-gen"
        )
        
        elapsed = time.time() - start
        
        # Parse output for URL
        url = None
        for line in result.stdout.split("\n"):
            if "Image available at:" in line:
                url = line.split("Image available at:")[-1].strip()
                break
        
        if result.returncode == 0 and url:
            print(f"  [OK] Generated in {elapsed:.1f}s")
            print(f"  URL: {url}")
            return {
                "success": True,
                "scenario": scenario["name"],
                "config": config,
                "url": url,
                "time_s": round(elapsed, 1)
            }
        else:
            print(f"  [ERROR] Generation failed")
            if result.stderr:
                print(f"  {result.stderr[:200]}")
            return {
                "success": False,
                "scenario": scenario["name"],
                "config": config,
                "error": result.stderr[:500] if result.stderr else "Unknown error"
            }
            
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Timeout after 5 minutes")
        return {
            "success": False,
            "scenario": scenario["name"],
            "config": config,
            "error": "Timeout"
        }
    except Exception as e:
        print(f"  [ERROR] {e}")
        return {
            "success": False,
            "scenario": scenario["name"],
            "config": config,
            "error": str(e)
        }


def main():
    print("=" * 70)
    print("GOLDEN RETRIEVER BATCH GENERATION EXPERIMENT")
    print("=" * 70)
    print(f"Total images to generate: 20")
    print(f"Scenarios available: {len(SCENARIOS)}")
    print(f"Config variations: {len(CONFIGS)}")
    
    results = []
    
    # Generate 20 images with varied scenarios and configs
    for i in range(20):
        scenario = SCENARIOS[i % len(SCENARIOS)]  # Cycle through scenarios
        config = CONFIGS[i % len(CONFIGS)]  # Cycle through configs
        
        result = generate_image(scenario, config, i + 1)
        results.append(result)
        
        # Small delay between generations
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    success = sum(1 for r in results if r["success"])
    failed = 20 - success
    total_time = sum(r.get("time_s", 0) for r in results if r["success"])
    
    print(f"\nSuccess: {success}/20")
    print(f"Failed: {failed}")
    print(f"Total generation time: {total_time:.1f}s")
    print(f"Average per image: {total_time/success:.1f}s" if success > 0 else "N/A")
    
    print("\n--- Generated Images ---")
    for r in results:
        if r["success"]:
            print(f"  {r['scenario']}: {r['url']}")
    
    if failed > 0:
        print("\n--- Failed ---")
        for r in results:
            if not r["success"]:
                print(f"  {r['scenario']}: {r.get('error', 'Unknown')[:80]}")
    
    # Save results
    output_file = f"/tmp/golden_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Results saved to: {output_file}")


if __name__ == "__main__":
    main()
