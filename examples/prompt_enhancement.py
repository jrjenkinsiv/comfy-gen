#!/usr/bin/env python3
"""Example: Using prompt enhancement with ComfyGen.

This example demonstrates how to use the prompt enhancer to automatically
improve prompts for better image generation quality.
"""

from utils.prompt_enhancer import enhance_prompt, is_available


def main():
    """Run prompt enhancement examples."""

    # Check if enhancement is available
    if not is_available():
        print("[ERROR] Prompt enhancement requires transformers library")
        print("[INFO] Install with: pip install transformers torch")
        return

    # Example 1: Simple enhancement
    print("\n=== Example 1: Simple Enhancement ===")
    simple_prompt = "a cat"
    print(f"Original: {simple_prompt}")
    enhanced = enhance_prompt(simple_prompt)
    print(f"Enhanced: {enhanced}")

    # Example 2: Enhancement with photorealistic style
    print("\n=== Example 2: Photorealistic Style ===")
    photo_prompt = "a sunset over mountains"
    print(f"Original: {photo_prompt}")
    enhanced = enhance_prompt(photo_prompt, style="photorealistic")
    print(f"Enhanced: {enhanced}")

    # Example 3: Enhancement with artistic style
    print("\n=== Example 3: Artistic Style ===")
    art_prompt = "a dragon"
    print(f"Original: {art_prompt}")
    enhanced = enhance_prompt(art_prompt, style="artistic")
    print(f"Enhanced: {enhanced}")

    # Example 4: Enhancement with game-asset style
    print("\n=== Example 4: Game Asset Style ===")
    game_prompt = "a battleship"
    print(f"Original: {game_prompt}")
    enhanced = enhance_prompt(game_prompt, style="game-asset")
    print(f"Enhanced: {enhanced}")

    print("\n=== CLI Usage Examples ===")
    print("\n# Basic enhancement:")
    print("python generate.py --workflow workflows/flux-dev.json \\")
    print("    --prompt 'a cat' \\")
    print("    --enhance-prompt \\")
    print("    --output /tmp/cat.png")

    print("\n# Enhancement with style:")
    print("python generate.py --workflow workflows/flux-dev.json \\")
    print("    --prompt 'a sunset' \\")
    print("    --enhance-prompt --enhance-style photorealistic \\")
    print("    --output /tmp/sunset.png")


if __name__ == "__main__":
    main()
