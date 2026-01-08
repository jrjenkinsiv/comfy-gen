#!/usr/bin/env python3
"""Batch experiment: 10 diverse prompts through LLM parser (async)"""

import sys
import time
import json
import asyncio
from datetime import datetime


async def main():
    # Check imports
    print("[1/5] Importing modules...")
    from comfy_gen.parsing.llm_intent import HybridLLMParser
    from comfy_gen.categories.registry import CategoryRegistry

    print("[2/5] Initializing parser...")
    parser = HybridLLMParser(
        llm_endpoint="http://192.168.1.253:11434/v1/chat/completions",
        llm_model="deepseek-r1:7b"
    )

    # Health check
    print("[3/5] LLM health check...")
    health = await parser.check_llm_health()
    print(f"  [OK] LLM ready: {health}")

    # Get inventory context
    print("[4/5] Loading inventory context...")
    registry = CategoryRegistry.get_instance()
    category_ids = registry.list_ids()
    print(f"  [OK] {len(category_ids)} categories available: {', '.join(category_ids[:5])}...")

    # Define 10 diverse test prompts (non-NSFW)
    prompts = [
        "professional headshot of a businesswoman at golden hour",
        "moody cyberpunk cityscape with neon reflections at night",
        "serene mountain landscape at sunset with dramatic clouds",
        "cute corgi puppy playing in autumn leaves",
        "vintage 1950s diner with chrome details and neon signs",
        "underwater scene with colorful coral reef and tropical fish",
        "cozy cabin interior with fireplace and winter view outside",
        "futuristic spaceship cockpit with holographic displays",
        "steampunk clockwork mechanism with brass gears",
        "japanese zen garden with cherry blossoms and koi pond"
    ]

    print(f"\n[5/5] Running {len(prompts)} LLM parsing experiments...")
    print("="*70)

    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] Prompt: \"{prompt}\"")
        
        start = time.time()
        try:
            # Parse with LLM
            parsed = await parser.parse(prompt)
            elapsed = time.time() - start
            
            # Get metadata
            metadata = parser.get_last_llm_metadata()
            
            result = {
                "prompt": prompt,
                "success": True,
                "parse_time_s": round(elapsed, 2),
                "category": parsed.get("category", "unknown"),
                "style": parsed.get("style", "unknown"),
                "subject": parsed.get("subject", "unknown"),
                "modifiers": parsed.get("modifiers", []),
                "llm_model": metadata.model if metadata else "unknown",
                "total_tokens": metadata.total_tokens if metadata else 0,
                "prompt_tokens": metadata.prompt_tokens if metadata else 0,
                "completion_tokens": metadata.completion_tokens if metadata else 0,
                "thinking_chars": len(metadata.thinking_text) if metadata and metadata.thinking_text else 0
            }
            
            print(f"  [OK] Category: {result['category']}")
            print(f"       Style: {result['style']}")
            print(f"       Subject: {result['subject']}")
            mods = result['modifiers'][:3] if result['modifiers'] else []
            print(f"       Modifiers: {mods}...")
            print(f"       Time: {elapsed:.1f}s | Tokens: {result['total_tokens']} | Thinking: {result['thinking_chars']} chars")
            
        except Exception as e:
            import traceback
            elapsed = time.time() - start
            result = {
                "prompt": prompt,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "parse_time_s": round(elapsed, 2)
            }
            print(f"  [ERROR] {e}")
        
        results.append(result)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    success = sum(1 for r in results if r["success"])
    failed = len(results) - success
    total_time = sum(r["parse_time_s"] for r in results)
    total_tokens = sum(r.get("total_tokens", 0) for r in results)

    print(f"\nSuccess: {success}/{len(results)} ({100*success//len(results)}%)")
    if failed > 0:
        print(f"Failed: {failed}")
    print(f"\nTiming:")
    print(f"  Total: {total_time:.1f}s")
    print(f"  Average: {total_time/len(results):.1f}s per prompt")
    print(f"  Min: {min(r['parse_time_s'] for r in results):.1f}s")
    print(f"  Max: {max(r['parse_time_s'] for r in results):.1f}s")

    print(f"\nTokens:")
    print(f"  Total: {total_tokens}")
    print(f"  Average: {total_tokens//len(results) if results else 0} per prompt")

    # Categories breakdown
    categories_found = {}
    for r in results:
        if r["success"]:
            cat = r.get("category", "unknown")
            categories_found[cat] = categories_found.get(cat, 0) + 1

    print(f"\nCategories detected:")
    for cat, count in sorted(categories_found.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Styles breakdown
    styles_found = {}
    for r in results:
        if r["success"]:
            style = r.get("style", "unknown")
            styles_found[style] = styles_found.get(style, 0) + 1

    print(f"\nStyles detected:")
    for style, count in sorted(styles_found.items(), key=lambda x: -x[1]):
        print(f"  {style}: {count}")

    # Save results
    output_file = f"/tmp/llm_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Results saved to: {output_file}")

    # Show failed prompts if any
    if failed > 0:
        print("\n[WARN] Failed prompts:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['prompt'][:40]}... : {r['error']}")


if __name__ == "__main__":
    asyncio.run(main())
