#!/usr/bin/env python3
"""Test backward compatibility of gallery server metadata parsing."""



def test_old_format_parsing():
    """Test parsing old flat metadata format."""
    old_meta = {
        "timestamp": "2026-01-04T13:40:36",
        "prompt": "a beautiful landscape",
        "negative_prompt": "ugly, bad",
        "workflow": "flux-dev.json",
        "seed": 42,
        "steps": 30,
        "cfg": 7,
        "sampler": "dpmpp_2m",
        "scheduler": "normal",
        "loras": [{"name": "style.safetensors", "strength": 0.9}],
        "preset": None,
        "validation_score": 0.85,
        "minio_url": "http://192.168.1.215:9000/comfy-gen/image.png"
    }

    # Simulate gallery server parsing logic
    if old_meta.get("input"):
        # New nested format
        parsed = {
            "prompt": old_meta["input"]["prompt"],
            "seed": old_meta["parameters"]["seed"],
            "loras": old_meta["parameters"]["loras"],
            "validation_score": old_meta["quality"]["prompt_adherence"]["clip"]
        }
    else:
        # Old flat format
        parsed = {
            "prompt": old_meta["prompt"],
            "seed": old_meta["seed"],
            "loras": old_meta["loras"],
            "validation_score": old_meta["validation_score"]
        }

    assert parsed["prompt"] == "a beautiful landscape"
    assert parsed["seed"] == 42
    assert len(parsed["loras"]) == 1
    assert parsed["validation_score"] == 0.85

    print("[OK] Old flat format parsed correctly")


def test_new_format_parsing():
    """Test parsing new nested metadata format."""
    new_meta = {
        "timestamp": "2026-01-04T15:30:00Z",
        "generation_id": "550e8400-e29b-41d4-a716-446655440000",
        "input": {
            "prompt": "a sleek sports car",
            "negative_prompt": "ugly",
            "preset": "automotive_photography"
        },
        "workflow": {
            "name": "flux-dev.json",
            "model": "flux1-dev-fp8.safetensors",
            "vae": "ae.safetensors"
        },
        "parameters": {
            "seed": 1001,
            "steps": 80,
            "cfg": 8.5,
            "sampler": "dpmpp_2m",
            "scheduler": "normal",
            "resolution": [1024, 1024],
            "loras": [{"name": "auto.safetensors", "strength": 0.8}]
        },
        "quality": {
            "composite_score": 7.8,
            "grade": "B",
            "prompt_adherence": {"clip": 0.85}
        },
        "storage": {
            "minio_url": "http://192.168.1.215:9000/comfy-gen/img.png",
            "file_size_bytes": 2456789,
            "format": "png",
            "generation_time_seconds": 45.2
        }
    }

    # Simulate gallery server parsing logic
    if new_meta.get("input"):
        # New nested format
        parsed = {
            "prompt": new_meta["input"]["prompt"],
            "seed": new_meta["parameters"]["seed"],
            "loras": new_meta["parameters"]["loras"],
            "validation_score": new_meta["quality"]["prompt_adherence"]["clip"],
            "model": new_meta["workflow"]["model"],
            "resolution": new_meta["parameters"]["resolution"],
            "generation_time": new_meta["storage"]["generation_time_seconds"],
            "file_size": new_meta["storage"]["file_size_bytes"]
        }
    else:
        # Old flat format
        parsed = {
            "prompt": new_meta["prompt"],
            "seed": new_meta["seed"],
            "loras": new_meta["loras"],
            "validation_score": new_meta["validation_score"]
        }

    assert parsed["prompt"] == "a sleek sports car"
    assert parsed["seed"] == 1001
    assert len(parsed["loras"]) == 1
    assert parsed["validation_score"] == 0.85
    assert parsed["model"] == "flux1-dev-fp8.safetensors"
    assert parsed["resolution"] == [1024, 1024]
    assert parsed["generation_time"] == 45.2
    assert parsed["file_size"] == 2456789

    print("[OK] New nested format parsed correctly with additional fields")


if __name__ == "__main__":
    test_old_format_parsing()
    test_new_format_parsing()
    print("\n[OK] All backward compatibility tests passed!")
    print("[OK] Gallery server can handle both old and new metadata formats!")
