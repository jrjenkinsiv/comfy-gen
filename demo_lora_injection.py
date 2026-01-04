#!/usr/bin/env python3
"""Demonstration of LoRA injection workflow transformation.

This script shows how the workflow JSON is modified when LoRAs are injected.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate import inject_loras, load_workflow

def print_workflow_summary(workflow, title):
    """Print a summary of the workflow structure."""
    print(f"\n{'='*60}")
    print(title)
    print('='*60)
    print(f"Total nodes: {len(workflow)}")
    print("\nNodes:")
    for node_id, node in sorted(workflow.items(), key=lambda x: int(x[0])):
        class_type = node.get('class_type', 'Unknown')
        print(f"  {node_id}: {class_type}", end='')
        
        if class_type == 'CheckpointLoaderSimple':
            print(f" ({node['inputs']['ckpt_name']})")
        elif class_type == 'LoraLoader':
            lora_name = node['inputs']['lora_name']
            strength = node['inputs']['strength_model']
            print(f" ({lora_name}, strength={strength})")
        elif class_type == 'CLIPTextEncode':
            text = node['inputs'].get('text', '')
            text_preview = text[:30] + '...' if len(text) > 30 else text
            print(f' ("{text_preview}")')
        elif class_type == 'KSampler':
            model_input = node['inputs'].get('model', [])
            print(f" (model from node {model_input[0] if model_input else '?'})")
        else:
            print()

def demo_single_lora():
    """Demonstrate single LoRA injection."""
    workflow = load_workflow('workflows/flux-dev.json')
    print_workflow_summary(workflow, "Original Workflow")
    
    loras = [("example_lora.safetensors", 0.8)]
    modified = inject_loras(workflow.copy(), loras)
    print_workflow_summary(modified, "After Injecting Single LoRA")

def demo_multiple_loras():
    """Demonstrate multiple LoRA injection."""
    workflow = load_workflow('workflows/flux-dev.json')
    
    loras = [
        ("style_lora.safetensors", 0.7),
        ("detail_lora.safetensors", 0.5),
        ("color_lora.safetensors", 0.6)
    ]
    modified = inject_loras(workflow.copy(), loras)
    print_workflow_summary(modified, "After Injecting 3 Chained LoRAs")

def demo_connections():
    """Show how connections are rewired."""
    workflow = load_workflow('workflows/flux-dev.json')
    
    print(f"\n{'='*60}")
    print("Connection Analysis")
    print('='*60)
    
    print("\nBEFORE LoRA injection:")
    print(f"  Node 2 (CLIP Text) uses clip from: {workflow['2']['inputs']['clip']}")
    print(f"  Node 3 (CLIP Text) uses clip from: {workflow['3']['inputs']['clip']}")
    print(f"  Node 5 (KSampler) uses model from: {workflow['5']['inputs']['model']}")
    
    loras = [("lora1.safetensors", 0.7), ("lora2.safetensors", 0.5)]
    modified = inject_loras(workflow.copy(), loras)
    
    print("\nAFTER LoRA injection (2 LoRAs):")
    print(f"  Node 8 (LoRA 1) uses model from: {modified['8']['inputs']['model']}")
    print(f"  Node 8 (LoRA 1) uses clip from: {modified['8']['inputs']['clip']}")
    print(f"  Node 9 (LoRA 2) uses model from: {modified['9']['inputs']['model']}")
    print(f"  Node 9 (LoRA 2) uses clip from: {modified['9']['inputs']['clip']}")
    print(f"  Node 2 (CLIP Text) uses clip from: {modified['2']['inputs']['clip']}")
    print(f"  Node 3 (CLIP Text) uses clip from: {modified['3']['inputs']['clip']}")
    print(f"  Node 5 (KSampler) uses model from: {modified['5']['inputs']['model']}")

def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("LoRA Injection Demonstration")
    print("="*60)
    
    demo_single_lora()
    demo_multiple_loras()
    demo_connections()
    
    print("\n" + "="*60)
    print("Demonstration Complete")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
