# ComfyGen Documentation

**Last verified:** 2026-01-05

Comprehensive documentation for ComfyGen - a programmatic image/video generation pipeline using ComfyUI.

## Documentation Structure

This documentation is organized into the following categories:

### 📚 Getting Started
- **[USAGE.md](USAGE.md)** - Primary usage guide with CLI and MCP server examples

### 🏗️ Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design, workflows, presets, and data flow
- **[API_REFERENCE.md](API_REFERENCE.md)** - Technical API documentation for internal modules

### 🎨 Model & LoRA Management
- **[MODEL_REGISTRY.md](MODEL_REGISTRY.md)** - Complete inventory of available models with download instructions
- **[LORA_GUIDE.md](LORA_GUIDE.md)** - LoRA selection, compatibility, and stacking strategies

### 🔧 Technical References
- **[MCP_SERVERS.md](MCP_SERVERS.md)** - MCP server tools and integration documentation
- **[METADATA_SCHEMA.md](METADATA_SCHEMA.md)** - JSON metadata format for experiment tracking
- **[QUALITY_SYSTEM.md](QUALITY_SYSTEM.md)** - Image quality assessment and validation system

### 🔞 Specialized Guides
- **[NSFW_GUIDE.md](NSFW_GUIDE.md)** - NSFW generation techniques, models, and best practices

---

## I Want To...

### Generate Images or Videos

**First time setup:**
1. Start with [USAGE.md](USAGE.md#quick-start) for basic generation examples
2. Check [MODEL_REGISTRY.md](MODEL_REGISTRY.md) to see available models
3. Review [ARCHITECTURE.md](ARCHITECTURE.md#workflows) to understand workflow selection

**Generate an image:**
```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png
```
See [USAGE.md - CLI Usage](USAGE.md#cli-usage) for comprehensive examples.

**Generate a video:**
```bash
python3 generate.py --workflow workflows/wan22-t2v.json \
    --prompt "camera slowly pans across mountains" \
    --output /tmp/video.mp4
```
See [USAGE.md - Video Generation](USAGE.md#video-generation) for details.

### Work with Models and LoRAs

**Download a new model:**
```bash
python scripts/download_model.py --model-id 43331 --type checkpoint
```
See [MODEL_REGISTRY.md - Quick Download](MODEL_REGISTRY.md#quick-download) for all download options.

**Choose the right LoRA:**
- Read [LORA_GUIDE.md](LORA_GUIDE.md) to understand video vs image LoRA compatibility
- Check [LORA_GUIDE.md - Verified LoRAs](LORA_GUIDE.md#verified-sd-15-image-loras-civitai-confirmed) for safe options
- **CRITICAL:** Never use video LoRAs (Wan Video 14B) for image generation (SD 1.5/SDXL)

**Stack multiple LoRAs:**
```bash
--lora "polyhedron_skin.safetensors:0.4" \
--lora "add_detail.safetensors:0.5"
```
See [LORA_GUIDE.md - LoRA Stacking Best Practices](LORA_GUIDE.md#lora-stacking-best-practices) for strength guidelines.

### Use MCP Servers (AI Assistant Integration)

**Setup MCP servers:**
1. Review [MCP_SERVERS.md - Configuration](MCP_SERVERS.md#configuration)
2. Copy [`mcp_config.json`](../mcp_config.json) to your Claude/VS Code settings
3. Set environment variables: `CIVITAI_API_KEY`, `HF_TOKEN`

**Available MCP tools:**
- **comfy-gen server** - Generate images/videos, list models, check server status
- **civitai server** - Search and verify CivitAI models
- **huggingface server** - Search HuggingFace models and datasets

See [MCP_SERVERS.md](MCP_SERVERS.md) for complete tool reference.

### Understand Quality and Validation

**Validate generated images:**
```bash
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a cat" \
    --validate --auto-retry --retry-limit 3
```
See [USAGE.md - Validation](USAGE.md#validation) for how validation works.

**Understand quality metrics:**
- Read [QUALITY_SYSTEM.md](QUALITY_SYSTEM.md) for the academic research behind quality assessment
- Key insight: **Validation** (prompt match) and **Quality** (technical excellence) are separate dimensions
- See [QUALITY_SYSTEM.md - Two Separate Pipelines](QUALITY_SYSTEM.md#key-insight-two-separate-pipelines)

### Generate NSFW Content

**IMPORTANT:** NSFW content stays local (MinIO only), never committed to git.

1. Read [NSFW_GUIDE.md](NSFW_GUIDE.md) for comprehensive techniques
2. Choose appropriate models: [NSFW_GUIDE.md - Model Selection](NSFW_GUIDE.md#model-selection)
3. Use verified image LoRAs: [NSFW_GUIDE.md - Verified LoRAs](NSFW_GUIDE.md#verified-loras)
4. Apply proper CFG/steps: [NSFW_GUIDE.md - Technical Settings](NSFW_GUIDE.md#technical-settings)

**Quick example:**
```bash
python3 generate.py --workflow workflows/majicmix-realistic.json \
    --prompt "detailed explicit prompt here" \
    --lora "airoticart_penis.safetensors:0.85" \
    --steps 70 --cfg 9.0
```

### Understand System Architecture

**See the big picture:**
- [ARCHITECTURE.md - System Overview](ARCHITECTURE.md#system-overview) - Infrastructure diagram and data flow
- [ARCHITECTURE.md - Workflows](ARCHITECTURE.md#workflows) - How workflow JSON files work
- [ARCHITECTURE.md - Metadata Tracking](ARCHITECTURE.md#metadata-tracking) - Experiment reproducibility

**Key infrastructure:**
| Machine | Role | IP |
|---------|------|-----|
| magneto | Development workstation | 192.168.1.124 |
| moira | ComfyUI server + MinIO + GPU (RTX 5090) | 192.168.1.215 |
| ant-man | GitHub Actions runner (ARM64) | 192.168.1.253 |

### Track Experiments and Reproduce Results

**Metadata tracking:**
Every generation creates a JSON sidecar file with complete parameters.

See [METADATA_SCHEMA.md](METADATA_SCHEMA.md) for:
- Schema structure and fields
- How to reproduce generations from metadata
- Quality score storage format

**Reproduce a previous generation:**
```bash
# Metadata is saved alongside images
cat /tmp/sunset.png.json
# Contains: prompt, workflow, seed, steps, cfg, loras, etc.
```

### Troubleshoot Issues

**Common problems:**

| Issue | Solution | Documentation |
|-------|----------|---------------|
| LoRA causes distorted anatomy | Using video LoRA for images | [LORA_GUIDE.md - Video vs Image](LORA_GUIDE.md#critical-video-vs-image-loras) |
| Image doesn't match prompt | Increase CFG, add weights | [USAGE.md - Prompt Engineering](USAGE.md#prompt-engineering) |
| ComfyUI not responding | Check server status | [USAGE.md - Error Handling](USAGE.md#error-handling) |
| Model not found | Verify installation path | [MODEL_REGISTRY.md - Directory Structure](MODEL_REGISTRY.md#directory-structure) |
| Quality issues | Review quality metrics | [QUALITY_SYSTEM.md - Troubleshooting](QUALITY_SYSTEM.md#troubleshooting) |

---

## Related Resources

### Configuration Files
- **[`mcp_config.json`](../mcp_config.json)** - MCP server configuration for AI assistants
- **[`presets.yaml`](../presets.yaml)** - Pre-configured generation presets
- **[`lora_catalog.yaml`](../lora_catalog.yaml)** - LoRA inventory with semantic tags
- **[`prompt_catalog.yaml`](../prompt_catalog.yaml)** - Tested prompt templates

### Workflows
- **`workflows/flux-dev.json`** - Flux image generation (primary)
- **`workflows/sd15-img2img.json`** - SD 1.5 image-to-image
- **`workflows/wan22-t2v.json`** - Wan 2.2 text-to-video
- **`workflows/wan22-i2v.json`** - Wan 2.2 image-to-video

See [ARCHITECTURE.md - Workflows](ARCHITECTURE.md#workflows) for complete workflow documentation.

### Scripts
- **`scripts/download_model.py`** - Download models from CivitAI/HuggingFace
- **`scripts/civitai_audit.py`** - Verify LoRA compatibility via CivitAI API
- **`scripts/start_comfyui.py`** - Start ComfyUI server on moira

---

## Quick Reference by File

### [USAGE.md](USAGE.md)
**Primary usage guide** - Start here for all generation tasks.

**Key sections:**
- Quick start examples (image, video, img2img)
- CLI parameter reference
- Presets system usage
- MCP server setup and tools
- Prompt engineering techniques
- Error handling procedures

**Use this when:** You want to generate images/videos or integrate with AI assistants.

### [ARCHITECTURE.md](ARCHITECTURE.md)
**System design documentation** - Understand how ComfyGen works internally.

**Key sections:**
- Infrastructure overview and data flow
- Workflow JSON structure
- Generation presets system
- Dynamic LoRA injection mechanics
- Metadata tracking implementation

**Use this when:** You need to understand system internals, modify workflows, or extend functionality.

### [MODEL_REGISTRY.md](MODEL_REGISTRY.md)
**Complete model inventory** - All available models with download instructions.

**Key sections:**
- Quick download commands
- API key setup (CivitAI, HuggingFace)
- Directory structure on moira
- Checkpoint models (Flux, SD 1.5, SDXL, Wan)
- LoRA inventory with file sizes
- VAE and encoder models

**Use this when:** You need to download models, verify installations, or check model availability.

### [LORA_GUIDE.md](LORA_GUIDE.md)
**LoRA selection and compatibility** - Critical guide to avoid common mistakes.

**Key sections:**
- **CRITICAL:** Video vs Image LoRA compatibility
- Hash lookup method for verification
- Verified SD 1.5 image LoRAs (CivitAI confirmed)
- Stacking strategies and strength guidelines
- Common mistakes to avoid

**Use this when:** You're adding LoRAs to generations and need to ensure compatibility.

### [MCP_SERVERS.md](MCP_SERVERS.md)
**MCP server tools documentation** - AI assistant integration reference.

**Key sections:**
- MCP server configuration
- comfy-gen server tools (generation, model listing, server management)
- civitai server tools (model search, metadata lookup)
- huggingface server tools (model/dataset search)
- Tool parameter reference

**Use this when:** You're using Claude, VS Code, or other MCP-compatible AI assistants.

### [METADATA_SCHEMA.md](METADATA_SCHEMA.md)
**JSON metadata format** - Experiment tracking and reproducibility.

**Key sections:**
- Schema structure (nested vs flat format)
- Complete field reference
- Reproduction workflow
- Quality score storage
- Multi-generation batch tracking

**Use this when:** You need to reproduce experiments, parse metadata, or track quality scores.

### [QUALITY_SYSTEM.md](QUALITY_SYSTEM.md)
**Quality assessment design** - Academic research-based validation system.

**Key sections:**
- Problem statement and research findings
- Two-dimension quality model (validation + quality)
- Metric selection (CLIP, ImageReward, BRISQUE, Aesthetic)
- Implementation design
- Quality score thresholds

**Use this when:** You need to understand quality metrics or implement quality improvements.

### [NSFW_GUIDE.md](NSFW_GUIDE.md)
**NSFW generation best practices** - Comprehensive explicit content generation guide.

**Key sections:**
- Core principles (terminology, model matching, quality)
- Model selection (image and video models)
- LoRA configuration and stacking
- Prompt engineering techniques
- Technical settings (steps, CFG, resolution)
- Example prompts and troubleshooting

**Use this when:** You're generating explicit adult content and need optimal results.

### [API_REFERENCE.md](API_REFERENCE.md)
**Technical API documentation** - Internal module and function reference.

**Key sections:**
- `generate.py` functions and CLI parameters
- `comfy_gen.validation` module
- Script utilities
- Code examples for programmatic usage

**Use this when:** You're writing code that imports ComfyGen modules or need internal API details.

---

## Documentation Standards

All ComfyGen documentation follows these conventions:

1. **Markdown format** - `.md` files with clear headings and code blocks
2. **Table of contents** - Major docs include TOC for easy navigation
3. **Code examples** - Every technique includes working command examples
4. **Cross-references** - Links to related docs for context
5. **Practical focus** - Solutions to real problems, not theoretical discussions

---

## Contributing to Docs

When adding or updating documentation:

1. **Update this index** if adding new files
2. **Add to appropriate category** (Getting Started, Architecture, etc.)
3. **Include in "I want to..." section** if it's a common task
4. **Cross-reference related docs** to help navigation
5. **Follow existing format** - TOC, examples, practical focus

---

**Last Updated:** 2026-01-05

---

**Documentation Policy:** NO DOCUMENT PROLIFERATION. All documentation files listed in this index are authoritative references. Do NOT create new documentation files without explicit approval. Add new infrastructure information to existing docs only.
