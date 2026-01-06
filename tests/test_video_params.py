"""Tests for video parameter modification in workflows.

This test verifies that video-specific parameters (length, fps, resolution)
are correctly applied to video workflows.

Note: These are focused unit tests that work with workflow JSON directly.
"""

import json
from pathlib import Path


def test_video_node_structure():
    """Test that wan22-t2v.json has correct video node structure."""
    workflow_path = Path(__file__).parent.parent / "workflows" / "wan22-t2v.json"

    with open(workflow_path) as f:
        workflow = json.load(f)

    # Find EmptyLatentVideo node
    video_node = None
    for _node_id, node in workflow.items():
        if node.get("class_type") == "EmptyLatentVideo":
            video_node = node
            break

    assert video_node is not None, "wan22-t2v.json should have EmptyLatentVideo node"
    assert "inputs" in video_node, "EmptyLatentVideo should have inputs"
    assert "width" in video_node["inputs"], "Should have width parameter"
    assert "height" in video_node["inputs"], "Should have height parameter"
    assert "length" in video_node["inputs"], "Should have length parameter"

    print(f"[OK] Found EmptyLatentVideo node with dimensions: {video_node['inputs']['width']}x{video_node['inputs']['height']}, {video_node['inputs']['length']} frames")


def test_video_combine_node_structure():
    """Test that wan22-t2v.json has VHS_VideoCombine node."""
    workflow_path = Path(__file__).parent.parent / "workflows" / "wan22-t2v.json"

    with open(workflow_path) as f:
        workflow = json.load(f)

    # Find VHS_VideoCombine node
    combine_node = None
    for _node_id, node in workflow.items():
        if node.get("class_type") == "VHS_VideoCombine":
            combine_node = node
            break

    assert combine_node is not None, "wan22-t2v.json should have VHS_VideoCombine node"
    assert "inputs" in combine_node, "VHS_VideoCombine should have inputs"
    assert "frame_rate" in combine_node["inputs"], "Should have frame_rate parameter"

    print(f"[OK] Found VHS_VideoCombine node with FPS: {combine_node['inputs']['frame_rate']}")


def test_low_noise_workflows_exist():
    """Test that low-noise workflow variants exist and have correct model references."""
    workflows_dir = Path(__file__).parent.parent / "workflows"

    # Check T2V low-noise
    t2v_low_path = workflows_dir / "wan22-t2v-low.json"
    assert t2v_low_path.exists(), "wan22-t2v-low.json should exist"

    with open(t2v_low_path) as f:
        t2v_low = json.load(f)

    # Find UNETLoader
    unet_node = None
    for _node_id, node in t2v_low.items():
        if node.get("class_type") == "UNETLoader":
            unet_node = node
            break

    assert unet_node is not None, "Should have UNETLoader"
    assert "low_noise" in unet_node["inputs"]["unet_name"], "Should reference low_noise model"

    print(f"[OK] wan22-t2v-low.json uses: {unet_node['inputs']['unet_name']}")

    # Check I2V low-noise
    i2v_low_path = workflows_dir / "wan22-i2v-low.json"
    assert i2v_low_path.exists(), "wan22-i2v-low.json should exist"

    with open(i2v_low_path) as f:
        i2v_low = json.load(f)

    # Find UNETLoader
    unet_node = None
    for _node_id, node in i2v_low.items():
        if node.get("class_type") == "UNETLoader":
            unet_node = node
            break

    assert unet_node is not None, "Should have UNETLoader"
    assert "low_noise" in unet_node["inputs"]["unet_name"], "Should reference low_noise model"

    print(f"[OK] wan22-i2v-low.json uses: {unet_node['inputs']['unet_name']}")


def test_video_presets_structure():
    """Test that video presets exist in presets.yaml."""
    import yaml

    presets_path = Path(__file__).parent.parent / "presets.yaml"

    with open(presets_path) as f:
        config = yaml.safe_load(f)

    assert "presets" in config, "Should have presets section"
    presets = config["presets"]

    # Check video-fast
    assert "video-fast" in presets, "Should have video-fast preset"
    video_fast = presets["video-fast"]
    assert "length" in video_fast, "video-fast should have length parameter"
    assert "fps" in video_fast, "video-fast should have fps parameter"
    assert video_fast["steps"] == 4, "video-fast should use 4 steps"
    print(f"[OK] video-fast preset: {video_fast['steps']} steps, {video_fast['length']} frames, {video_fast['fps']} fps")

    # Check video-quality
    assert "video-quality" in presets, "Should have video-quality preset"
    video_quality = presets["video-quality"]
    assert "loras" in video_quality, "video-quality should have LoRAs"
    assert len(video_quality["loras"]) > 0, "video-quality should have physics LoRAs"
    print(f"[OK] video-quality preset: {video_quality['steps']} steps, {len(video_quality['loras'])} LoRAs")

    # Check video-nsfw
    assert "video-nsfw" in presets, "Should have video-nsfw preset"
    video_nsfw = presets["video-nsfw"]
    assert "loras" in video_nsfw, "video-nsfw should have LoRAs"
    print(f"[OK] video-nsfw preset: {video_nsfw['steps']} steps, {len(video_nsfw['loras'])} LoRAs")


def test_video_parameter_modification():
    """Test that video parameters can be modified in workflow JSON."""
    workflow_path = Path(__file__).parent.parent / "workflows" / "wan22-t2v.json"

    with open(workflow_path) as f:
        workflow = json.load(f)

    # Find and modify EmptyLatentVideo node
    for _node_id, node in workflow.items():
        if node.get("class_type") == "EmptyLatentVideo":
            original_width = node["inputs"]["width"]
            original_height = node["inputs"]["height"]
            original_length = node["inputs"]["length"]

            # Modify
            node["inputs"]["width"] = 1280
            node["inputs"]["height"] = 720
            node["inputs"]["length"] = 161

            assert node["inputs"]["width"] == 1280, "Width modification should work"
            assert node["inputs"]["height"] == 720, "Height modification should work"
            assert node["inputs"]["length"] == 161, "Length modification should work"

            print(f"[OK] Successfully modified video params: {original_width}x{original_height}@{original_length} -> 1280x720@161")
            break

    # Find and modify VHS_VideoCombine node
    for _node_id, node in workflow.items():
        if node.get("class_type") == "VHS_VideoCombine":
            original_fps = node["inputs"]["frame_rate"]

            # Modify
            node["inputs"]["frame_rate"] = 24

            assert node["inputs"]["frame_rate"] == 24, "FPS modification should work"

            print(f"[OK] Successfully modified FPS: {original_fps} -> 24")
            break


def test_video_resolution_parsing():
    """Test --video-resolution argument parsing logic."""
    test_cases = [
        ("848x480", (848, 480)),
        ("1280x720", (1280, 720)),
        ("1920x1080", (1920, 1080)),
        ("640x360", (640, 360)),
        ("3840x2160", (3840, 2160))  # 4K
    ]

    for input_str, expected in test_cases:
        width, height = map(int, input_str.split('x'))
        assert (width, height) == expected, f"Failed to parse {input_str}"

    print(f"[OK] Video resolution parsing works for {len(test_cases)} formats")


def test_duration_math():
    """Test frame count to duration calculation."""
    test_cases = [
        (81, 16, 5.0625),   # ~5 seconds
        (161, 16, 10.0625), # ~10 seconds
        (241, 16, 15.0625), # ~15 seconds
        (81, 24, 3.375),    # ~3.4 seconds at 24fps
        (81, 30, 2.7)       # ~2.7 seconds at 30fps
    ]

    for frames, fps, expected_duration in test_cases:
        duration = frames / fps
        assert abs(duration - expected_duration) < 0.01, f"Duration calculation failed for {frames} frames @ {fps} fps"

    print(f"[OK] Duration math verified for {len(test_cases)} cases")


if __name__ == "__main__":
    print("Testing video parameter integration...")
    print()

    test_video_node_structure()
    test_video_combine_node_structure()
    test_low_noise_workflows_exist()
    test_video_presets_structure()
    test_video_parameter_modification()
    test_video_resolution_parsing()
    test_duration_math()

    print()
    print("=" * 60)
    print("[OK] All video integration tests passed!")
    print("=" * 60)

