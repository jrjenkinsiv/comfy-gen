# MCP Server Test Results

**Date:** 2025-01-04  
**MCP Version:** 1.25.0  
**ComfyUI Version:** 0.3.59  
**GPU:** NVIDIA GeForce RTX 5090 (32GB VRAM)  

## Test Summary

| Category | Tool | Status | Notes |
|----------|------|--------|-------|
| **Generation** | generate.py CLI | ✅ Pass | Full workflow with MinIO upload |
| **Models** | list_models | ✅ Pass | Returns 1 checkpoint |
| **Models** | list_loras | ✅ Pass | Returns 45 LoRAs with tags |
| **Models** | suggest_model | ✅ Pass | Recommends based on task |
| **Models** | suggest_loras | ⚠️ Partial | Works but returns few matches |
| **Models** | search_civitai | ✅ Pass | Fixed API params |
| **Gallery** | list_images | ✅ Pass | Returns 10 recent images |
| **Prompts** | expand_prompt | ✅ Pass | Adds quality tags |
| **Prompts** | analyze_prompt | ✅ Pass | Detects elements |
| **Control** | get_system_status | ⚠️ Partial | Returns online, GPU parsing needs fix |
| **Control** | get_queue_status | ✅ Pass | Shows queue state |
| **Video** | generate_video | ❌ Fail | EmptyLatentVideo node missing |
| **Video** | image_to_video | ❓ Not tested | Workflow needs fix |

## Bugs Fixed During Testing

### 1. Workflow Metadata Bug
**Issue:** ComfyUI rejected workflows with `#_workflow_metadata` key  
**Fix:** Removed `_workflow_metadata` from all 4 workflow JSON files  
**Commit:** `85c4147`

### 2. CivitAI API Bug
**Issue:** Search returned 0 results due to incompatible `page` parameter  
**Fix:** Removed `page` param when using query search (API requires cursor-based pagination)  
**Commit:** `85c4147`

## Known Issues

### Video Generation Blocked
The Wan 2.2 text-to-video workflow uses `EmptyLatentVideo` which doesn't exist in ComfyUI.
Available alternatives:
- `EmptyCosmosLatentVideo`
- `EmptyHunyuanLatentVideo`
- `EmptyLTXVLatentVideo`
- `EmptyMochiLatentVideo`

**Action:** Need to update wan22-t2v.json workflow or use different video node.

### LoRA Suggestions
The `suggest_loras` function returns few matches because:
- Catalog is video-focused (Wan 2.2 LoRAs)
- Few Flux/SD image LoRAs cataloged

## Test Images Generated

| Filename | Size | URL |
|----------|------|-----|
| 20260104_015019_mcp_test_full.png | 379KB | [Link](http://192.168.1.215:9000/comfy-gen/20260104_015019_mcp_test_full.png) |
| 20260104_014420_mcp_test_portrait.png | 419KB | [Link](http://192.168.1.215:9000/comfy-gen/20260104_014420_mcp_test_portrait.png) |

## Recommendations

1. **Update video workflows** - Replace `EmptyLatentVideo` with working node
2. **Expand LoRA catalog** - Add more Flux/SD LoRAs for image generation
3. **Fix GPU parsing** - Update `get_system_status` to read from `devices[0]`
4. **Add MCP tool tests** - Create pytest suite for MCP tools

