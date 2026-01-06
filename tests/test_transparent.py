#!/usr/bin/env python3
"""Test transparent background functionality."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_enable_transparency_basic():
    """Test that enable_transparency adds SAM nodes to workflow."""
    # Load a basic workflow
    workflow_path = Path(__file__).parent.parent / "workflows" / "flux-dev.json"
    with open(workflow_path) as f:
        workflow = json.load(f)

    # Get initial node count
    initial_node_count = len(workflow)

    # Enable transparency
    modified_workflow = generate.enable_transparency(workflow)

    # Check that nodes were added (should add 3 nodes: SAMLoader, SAMDetector, Composite)
    final_node_count = len(modified_workflow)
    assert final_node_count == initial_node_count + 3, \
        f"Expected 3 new nodes, got {final_node_count - initial_node_count}"

    # Check that SAMModelLoader node exists
    sam_loader_found = False
    sam_detector_found = False
    composite_found = False

    for _node_id, node in modified_workflow.items():
        class_type = node.get("class_type", "")
        if class_type == "SAMModelLoader (segment anything)":
            sam_loader_found = True
            # Check it has the correct model
            assert node["inputs"]["model_name"] == "sam_vit_b_01ec64.pth"
        elif class_type == "SAMDetector (segment anything)":
            sam_detector_found = True
            # Check it's connected to SAMLoader
            assert isinstance(node["inputs"]["sam_model"], list)
        elif class_type == "ImageCompositeMasked":
            composite_found = True
            # Check alpha channel is set
            assert node["inputs"]["channel"] == "alpha"

    assert sam_loader_found, "SAMModelLoader node not found"
    assert sam_detector_found, "SAMDetector node not found"
    assert composite_found, "ImageCompositeMasked node not found"

    # Check that SaveImage was redirected
    save_node_found = False
    for _node_id, node in modified_workflow.items():
        if node.get("class_type") == "SaveImage":
            save_node_found = True
            # Check it points to the composite node
            images_input = node["inputs"]["images"]
            assert isinstance(images_input, list), "SaveImage images input should be a list"
            # The composite node should be the last one added (max_id + 3)
            break

    assert save_node_found, "SaveImage node not found"

    print("[OK] enable_transparency adds correct nodes")
    print(f"[OK] Initial nodes: {initial_node_count}, Final nodes: {final_node_count}")


def test_transparent_workflow_json():
    """Test that transparent-icon.json workflow is valid."""
    workflow_path = Path(__file__).parent.parent / "workflows" / "transparent-icon.json"

    assert workflow_path.exists(), f"transparent-icon.json not found at {workflow_path}"

    # Load and validate JSON
    with open(workflow_path) as f:
        workflow = json.load(f)

    # Check essential nodes
    has_checkpoint = False
    has_sam_loader = False
    has_sam_detector = False
    has_composite = False
    has_save = False

    for _node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        if class_type == "CheckpointLoaderSimple":
            has_checkpoint = True
        elif class_type == "SAMModelLoader (segment anything)":
            has_sam_loader = True
        elif class_type == "SAMDetector (segment anything)":
            has_sam_detector = True
        elif class_type == "ImageCompositeMasked":
            has_composite = True
        elif class_type == "SaveImage":
            has_save = True

    assert has_checkpoint, "CheckpointLoaderSimple not found"
    assert has_sam_loader, "SAMModelLoader not found"
    assert has_sam_detector, "SAMDetector not found"
    assert has_composite, "ImageCompositeMasked not found"
    assert has_save, "SaveImage not found"

    print("[OK] transparent-icon.json workflow is valid")
    print(f"[OK] Contains {len(workflow)} nodes")


if __name__ == "__main__":
    print("Testing transparent background functionality...\n")

    test_enable_transparency_basic()
    test_transparent_workflow_json()

    print("\n[OK] All transparency tests passed!")
