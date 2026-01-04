#!/usr/bin/env python3
"""Example demonstrating the enhanced metadata JSON schema."""

import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path to import generate
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def demonstrate_metadata_schema():
    """Demonstrate the new nested metadata structure."""
    
    # Create a sample workflow
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"}
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"}
        },
        "3": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
        },
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "steps": 80,
                "cfg": 8.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "normal"
            }
        },
        "5": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "automotive_detail.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0.8
            }
        }
    }
    
    # Extract workflow parameters
    workflow_params = generate.extract_workflow_params(workflow)
    loras = generate.extract_loras_from_workflow(workflow)
    
    # Create a temporary file to simulate output
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False) as f:
        # Write some fake image data
        f.write(b"PNG fake image content" * 100000)
        temp_output_path = f.name
    
    try:
        # Generate metadata with all new features
        metadata = generate.create_metadata_json(
            workflow_path="workflows/flux-dev.json",
            prompt="a sleek sports car on a mountain road, cinematic lighting, highly detailed, 8k resolution",
            negative_prompt="bad quality, blurry, low resolution, watermark, text",
            workflow_params=workflow_params,
            loras=loras,
            preset="high-quality",
            validation_score=0.87,
            minio_url="http://192.168.1.215:9000/comfy-gen/20260104_153000_output.png",
            workflow=workflow,
            output_path=temp_output_path,
            generation_time_seconds=45.2
        )
        
        # Display the metadata structure
        print("=" * 80)
        print("ENHANCED METADATA JSON SCHEMA EXAMPLE")
        print("=" * 80)
        print(json.dumps(metadata, indent=2))
        print("=" * 80)
        
        # Verify all expected fields are present
        print("\nField Verification:")
        print(f"  ✓ generation_id: {metadata['generation_id']}")
        print(f"  ✓ timestamp: {metadata['timestamp']}")
        print(f"\n  Input:")
        print(f"    ✓ prompt: {metadata['input']['prompt'][:50]}...")
        print(f"    ✓ negative_prompt: {metadata['input']['negative_prompt'][:30]}...")
        print(f"    ✓ preset: {metadata['input']['preset']}")
        print(f"\n  Workflow:")
        print(f"    ✓ name: {metadata['workflow']['name']}")
        print(f"    ✓ model: {metadata['workflow']['model']}")
        print(f"    ✓ vae: {metadata['workflow']['vae']}")
        print(f"\n  Parameters:")
        print(f"    ✓ seed: {metadata['parameters']['seed']}")
        print(f"    ✓ steps: {metadata['parameters']['steps']}")
        print(f"    ✓ cfg: {metadata['parameters']['cfg']}")
        print(f"    ✓ sampler: {metadata['parameters']['sampler']}")
        print(f"    ✓ scheduler: {metadata['parameters']['scheduler']}")
        print(f"    ✓ resolution: {metadata['parameters']['resolution']}")
        print(f"    ✓ loras: {len(metadata['parameters']['loras'])} LoRA(s)")
        print(f"\n  Quality:")
        print(f"    ✓ prompt_adherence.clip: {metadata['quality']['prompt_adherence']['clip']}")
        print(f"    ✓ composite_score: {metadata['quality']['composite_score']} (placeholder)")
        print(f"    ✓ grade: {metadata['quality']['grade']} (placeholder)")
        print(f"\n  Storage:")
        print(f"    ✓ minio_url: {metadata['storage']['minio_url']}")
        print(f"    ✓ file_size_bytes: {metadata['storage']['file_size_bytes']:,}")
        print(f"    ✓ format: {metadata['storage']['format']}")
        print(f"    ✓ generation_time_seconds: {metadata['storage']['generation_time_seconds']}")
        print(f"\n  Refinement:")
        print(f"    ✓ attempt: {metadata['refinement']['attempt']} (placeholder)")
        print(f"    ✓ max_attempts: {metadata['refinement']['max_attempts']} (placeholder)")
        
        print("\n[OK] All fields present in nested metadata structure!")
        print("[OK] Metadata is ready for experiment tracking and reproducibility!")
        
    finally:
        # Clean up temp file
        if Path(temp_output_path).exists():
            Path(temp_output_path).unlink()


if __name__ == "__main__":
    demonstrate_metadata_schema()
