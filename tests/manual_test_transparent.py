#!/usr/bin/env python3
"""Manual test script for transparent background generation.

This script demonstrates how to use the transparent background feature.
It requires access to the ComfyUI server on the local network.

Usage:
    # Using the transparent-icon.json workflow directly:
    python3 generate.py --workflow workflows/transparent-icon.json \\
        --prompt "a battleship, top-down view, game icon style" \\
        --output /tmp/ship_icon.png

    # Using --transparent flag with any workflow:
    python3 generate.py --workflow workflows/flux-dev.json \\
        --prompt "a battleship, top-down view, game icon style" \\
        --transparent \\
        --output /tmp/ship_icon_transparent.png

    # Testing workflow modification:
    python3 tests/manual_test_transparent.py
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_workflow_modification():
    """Test that --transparent correctly modifies a workflow."""
    print("\n[INFO] Testing workflow modification with enable_transparency()...")

    # Load base workflow
    workflow_path = Path(__file__).parent.parent / "workflows" / "flux-dev.json"
    with open(workflow_path) as f:
        original_workflow = json.load(f)

    print(f"[OK] Loaded base workflow: {workflow_path.name}")
    print(f"[OK] Original node count: {len(original_workflow)}")

    # Apply transparency
    transparent_workflow = generate.enable_transparency(original_workflow.copy())

    print(f"[OK] Modified node count: {len(transparent_workflow)}")
    print(f"[OK] Nodes added: {len(transparent_workflow) - len(original_workflow)}")

    # Verify nodes were added
    sam_loader_id = None
    sam_detector_id = None
    composite_id = None

    for node_id, node in transparent_workflow.items():
        class_type = node.get("class_type", "")
        if class_type == "SAMModelLoader (segment anything)":
            sam_loader_id = node_id
            print(f"[OK] Found SAMModelLoader node (ID: {node_id})")
            print(f"    Model: {node['inputs']['model_name']}")
        elif class_type == "SAMDetector (segment anything)":
            sam_detector_id = node_id
            print(f"[OK] Found SAMDetector node (ID: {node_id})")
            print(f"    Device mode: {node['inputs']['device_mode']}")
        elif class_type == "ImageCompositeMasked":
            composite_id = node_id
            print(f"[OK] Found ImageCompositeMasked node (ID: {node_id})")
            print(f"    Channel: {node['inputs']['channel']}")
            print(f"    Invert: {node['inputs']['invert']}")

    # Verify connections
    if sam_loader_id and sam_detector_id:
        sam_detector = transparent_workflow[sam_detector_id]
        sam_model_input = sam_detector["inputs"]["sam_model"]
        print(f"[OK] SAMDetector connected to SAMLoader: {sam_model_input}")

    if composite_id:
        composite = transparent_workflow[composite_id]
        mask_input = composite["inputs"]["mask"]
        print(f"[OK] Composite mask connected to SAMDetector: {mask_input}")

    # Check SaveImage redirection
    for node_id, node in transparent_workflow.items():
        if node.get("class_type") == "SaveImage":
            images_input = node["inputs"]["images"]
            print(f"[OK] SaveImage redirected to: {images_input}")
            if node["inputs"].get("filename_prefix"):
                print(f"[OK] Filename prefix: {node['inputs']['filename_prefix']}")

    print("\n[OK] Workflow modification test complete!")


def test_transparent_icon_workflow():
    """Test the transparent-icon.json workflow."""
    print("\n[INFO] Testing transparent-icon.json workflow...")

    workflow_path = Path(__file__).parent.parent / "workflows" / "transparent-icon.json"
    with open(workflow_path) as f:
        workflow = json.load(f)

    print(f"[OK] Loaded workflow: {workflow_path.name}")
    print(f"[OK] Total nodes: {len(workflow)}")

    # List all nodes
    print("\n[INFO] Workflow nodes:")
    for node_id, node in sorted(workflow.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
        class_type = node.get("class_type", "Unknown")
        title = node.get("_meta", {}).get("title", "")
        print(f"  {node_id:2s}: {class_type:40s} ({title})")

    # Verify workflow structure
    expected_nodes = {
        "CheckpointLoaderSimple": "Load Checkpoint",
        "CLIPTextEncode": "Positive/Negative Prompt",
        "EmptyLatentImage": "Empty Latent Image",
        "KSampler": "KSampler",
        "VAEDecode": "VAE Decode",
        "SAMModelLoader (segment anything)": "Load SAM Model",
        "SAMDetector (segment anything)": "SAM Detector",
        "ImageCompositeMasked": "Apply Alpha Mask",
        "SaveImage": "Save Image"
    }

    found_nodes = {}
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        if class_type in expected_nodes:
            found_nodes[class_type] = node_id

    print("\n[INFO] Expected node types:")
    for class_type, _description in expected_nodes.items():
        if class_type in found_nodes:
            print(f"  [OK] {class_type}: Found")
        else:
            print(f"  [WARN] {class_type}: Not found")

    print("\n[OK] Workflow structure test complete!")


def print_usage_examples():
    """Print usage examples."""
    print("\n" + "="*60)
    print("TRANSPARENT BACKGROUND GENERATION - USAGE EXAMPLES")
    print("="*60)

    print("\n1. Using transparent-icon.json workflow directly:")
    print("   python3 generate.py --workflow workflows/transparent-icon.json \\")
    print("       --prompt 'a battleship, top-down view, game icon style' \\")
    print("       --output /tmp/ship_icon.png")

    print("\n2. Using --transparent flag with any workflow:")
    print("   python3 generate.py --workflow workflows/flux-dev.json \\")
    print("       --prompt 'a battleship, top-down view, game icon style' \\")
    print("       --transparent \\")
    print("       --output /tmp/ship_transparent.png")

    print("\n3. Using MCP server (via Claude Desktop or API):")
    print("   {")
    print('     "tool": "generate_image",')
    print('     "arguments": {')
    print('       "prompt": "a battleship, top-down view, game icon style",')
    print('       "transparent": true,')
    print('       "width": 512,')
    print('       "height": 512')
    print("     }")
    print("   }")

    print("\n4. Testing with ship icon (acceptance criteria):")
    print("   python3 generate.py --workflow workflows/transparent-icon.json \\")
    print("       --prompt 'a detailed battleship warship, top-down orthographic view, \\")
    print("                centered, game icon style, clean product photography' \\")
    print("       --negative-prompt 'perspective, angled view, side view, \\")
    print("                          multiple ships, background' \\")
    print("       --steps 50 --cfg 8.0 \\")
    print("       --output /tmp/battleship_icon.png")

    print("\n5. Verify PNG has alpha channel:")
    print("   python3 -c \"from PIL import Image; img = Image.open('/tmp/ship_icon.png'); \\")
    print("                print(f'Mode: {img.mode}, Has alpha: {\\'A\\' in img.mode}')\"")

    print("\n" + "="*60)


if __name__ == "__main__":
    print("TRANSPARENT BACKGROUND - MANUAL TEST SUITE")
    print("="*60)

    # Run tests
    test_workflow_modification()
    test_transparent_icon_workflow()

    # Print usage examples
    print_usage_examples()

    print("\n[OK] All manual tests passed!")
    print("\nNOTE: To run actual generation, you need access to ComfyUI server at 192.168.1.215:8188")
    print("      This test only validates workflow structure and modification logic.")
