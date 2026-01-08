#!/usr/bin/env python3
"""Generate high-quality golden retriever images with various styles and resolutions."""

import subprocess
import time
import json
from pathlib import Path

# High-quality golden retriever prompts with varied styles
GOLDEN_EXPERIMENTS = [
    # Photorealistic - High detail
    {
        "name": "golden_photo_portrait",
        "workflow": "flux-dev-hires.json",
        "prompt": "golden retriever portrait, professional pet photography, studio lighting, sharp focus, detailed fur texture",
        "negative": "blurry, bad quality, cartoon, anime",
        "steps": 70,
        "cfg": 9.0,
    },
    # Action shot
    {
        "name": "golden_running_action",
        "workflow": "flux-dev-hires.json",
        "prompt": "golden retriever running through field, action photography, motion blur background, athletic dog",
        "negative": "static, blurry, deformed",
        "steps": 60,
        "cfg": 8.5,
    },
    # Anime style
    {
        "name": "golden_anime_kawaii",
        "workflow": "illustrious-anime.json",
        "prompt": "cute golden retriever puppy, anime style, chibi, kawaii, big eyes, fluffy",
        "negative": "realistic, photo, bad quality",
        "steps": 50,
        "cfg": 8.0,
    },
    # Watercolor painting
    {
        "name": "golden_watercolor",
        "workflow": "flux-dev-hires.json",
        "prompt": "golden retriever, watercolor painting style, artistic, soft colors, painterly",
        "negative": "photo, realistic, sharp",
        "steps": 50,
        "cfg": 7.5,
    },
    # High-res pony
    {
        "name": "golden_pony_scenic",
        "workflow": "pony-realism-hires.json",
        "prompt": "score_9, score_8_up, majestic golden retriever in mountain landscape, epic scenery, golden hour lighting",
        "negative": "score_6, bad quality, cartoon",
        "steps": 70,
        "cfg": 8.0,
    },
    # Beach scene
    {
        "name": "golden_beach_sunset",
        "workflow": "flux-dev-hires.json",
        "prompt": "golden retriever on beach at sunset, silhouette, waves, dramatic sky, cinematic",
        "negative": "daylight, bright, bad quality",
        "steps": 60,
        "cfg": 8.0,
    },
    # Snow scene
    {
        "name": "golden_snow_play",
        "workflow": "flux-dev-hires.json",
        "prompt": "golden retriever playing in snow, winter wonderland, fluffy snow, happy dog, cold breath visible",
        "negative": "summer, grass, bad quality",
        "steps": 65,
        "cfg": 8.5,
    },
    # Studio portrait extreme
    {
        "name": "golden_studio_extreme",
        "workflow": "pony-realism-hires.json",
        "prompt": "score_9, score_8_up, golden retriever, professional studio photography, black background, rim lighting, detailed fur",
        "negative": "score_6, outdoor, nature, bad quality",
        "steps": 80,
        "cfg": 9.0,
    },
    # Macro fur detail
    {
        "name": "golden_macro_fur",
        "workflow": "flux-dev-hires.json",
        "prompt": "extreme close-up golden retriever fur texture, macro photography, individual hair strands visible, golden cream color",
        "negative": "full body, face, blurry",
        "steps": 70,
        "cfg": 9.0,
    },
    # Puppy eyes closeup
    {
        "name": "golden_puppy_eyes",
        "workflow": "flux-dev-hires.json",
        "prompt": "golden retriever puppy face closeup, big innocent brown eyes, wet nose, adorable expression",
        "negative": "adult dog, full body, blurry",
        "steps": 60,
        "cfg": 8.5,
    },
]

def run_generation(exp):
    """Run a single generation experiment."""
    timestamp = int(time.time())
    output = f"/tmp/{exp['name']}_{timestamp}.png"
    
    cmd = [
        "python3", "generate.py",
        "--workflow", f"workflows/{exp['workflow']}",
        "--prompt", exp["prompt"],
        "--negative-prompt", exp["negative"],
        "--steps", str(exp["steps"]),
        "--cfg", str(exp["cfg"]),
        "--output", output,
    ]
    
    print(f"\n{'='*60}")
    print(f"Generating: {exp['name']}")
    print(f"Workflow: {exp['workflow']}")
    print(f"Steps: {exp['steps']}, CFG: {exp['cfg']}")
    print(f"Prompt: {exp['prompt'][:60]}...")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Extract score from output
    score = None
    url = None
    for line in result.stdout.split('\n'):
        if 'Score:' in line:
            try:
                score = float(line.split(':')[-1].strip())
            except:
                pass
        if 'Image available at:' in line:
            url = line.split('at:')[-1].strip()
    
    return {
        "name": exp["name"],
        "score": score,
        "url": url,
        "success": result.returncode == 0,
    }

def main():
    results = []
    
    for exp in GOLDEN_EXPERIMENTS:
        result = run_generation(exp)
        results.append(result)
        print(f"\n[RESULT] {result['name']}: Score={result['score']}, URL={result['url']}")
        time.sleep(2)  # Brief pause between generations
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY - Golden Retriever High Quality Batch")
    print("="*60)
    
    successful = [r for r in results if r['success'] and r['score']]
    if successful:
        scores = [r['score'] for r in successful]
        print(f"Generated: {len(successful)}/{len(GOLDEN_EXPERIMENTS)} images")
        print(f"Average Score: {sum(scores)/len(scores):.3f}")
        print(f"Best Score: {max(scores):.3f}")
        print(f"Worst Score: {min(scores):.3f}")
        
        print("\nAll Results (sorted by score):")
        for r in sorted(successful, key=lambda x: x['score'], reverse=True):
            print(f"  {r['score']:.3f} - {r['name']}: {r['url']}")
    
    # Save results
    with open('/tmp/golden_hires_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to /tmp/golden_hires_results.json")

if __name__ == "__main__":
    main()
