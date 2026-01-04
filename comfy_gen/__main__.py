#!/usr/bin/env python3
"""CLI entry point for comfy_gen.quality module.

Usage: python3 -m comfy_gen.quality <image_path> [prompt]
"""

from .quality import main

if __name__ == "__main__":
    main()
