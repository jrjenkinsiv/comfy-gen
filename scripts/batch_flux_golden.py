#!/usr/bin/env python3
"""Generate multiple golden retriever images with Flux Dev FP8."""

import subprocess
import json
from pathlib import Path

# Varied prompts for golden retrievers
PROMPTS = [
    ("flux_golden_puppy", "A fluffy golden retriever puppy sitting on a sunny lawn, photorealistic, 8k"),
    ("flux_golden_beach", "A golden retriever running on a beach at sunset, waves in background, photorealistic"),
    ("flux_golden_snow", "A golden retriever playing in fresh snow, breath visible, winter landscape"),
    ("flux_golden_forest", "A golden retriever hiking on a forest trail, dappled sunlight, autumn colors"),
    ("flux_golden_portrait", "Close-up portrait of a golden retriever, soft studio lighting, sharp details"),
    ("flux_golden_family", "A golden retriever lying on a living room rug, cozy home interior, warm lighting"),
    ("flux_golden_lake", "A golden retriever swimming in a crystal clear lake, mountains in background"),
    ("flux_golden_meadow", "A golden retriever in a field of wildflowers, golden hour lighting, bokeh"),
    ("flux_golden_rain", "A golden retriever with wet fur after rain, shaking off water droplets"),
    ("flux_golden_bed", "A sleepy golden retriever curled up on a cozy bed, soft blankets, peaceful"),
]

results = []

for name, prompt in PROMPTS:
    print(f"\n[INFO] Generating: {name}")
    print(f"[INFO] Prompt: {prompt[:60]}...")
    
    output_path = f"/tmp/{name}.png"
    
    result = subprocess.run([
        "python3", "generate.py",
        "--workflow", "workflows/flux-dev-proper.json",
        "--prompt", prompt,
        "--output", output_path
    ], capture_output=True, text=True, cwd="/Users/jrjenkinsiv/Development/comfy-gen")
    
    # Parse output for score
    score = None
    url = None
    for line in result.stdout.split("\n"):
        if "Score:" in line:
            try:
                score = float(line.split(":")[1].strip())
            except:
                pass
        if "Image available at:" in line:
            url = line.split(": ")[1].strip()
    
    results.append({
        "name": name,
        "prompt": prompt,
        "score": score,
        "url": url
    })
    
    print(f"[OK] Score: {score}")
    print(f"[OK] URL: {url}")

# Summary
print("\n" + "="*60)
print("FLUX GOLDEN RETRIEVER BATCH SUMMARY")
print("="*60)

scores = [r["score"] for r in results if r["score"]]
if scores:
    avg_score = sum(scores) / len(scores)
    print(f"Average Score: {avg_score:.3f}")
    print(f"Best Score: {max(scores):.3f}")
    print(f"Worst Score: {min(scores):.3f}")

print("\nAll URLs:")
for r in results:
    print(f"  {r['name']}: {r['url']} (Score: {r['score']})")

# Save results
with open("/tmp/flux_batch_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\n[OK] Results saved to /tmp/flux_batch_results.json")
