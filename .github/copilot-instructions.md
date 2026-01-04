# Copilot & Agent Instructions

## 1. Agent Roles & Autonomous Workflow

### VS Code Agent (Claude) - The Orchestrator
**Role:** Autonomous workflow manager. You do not write application code unless fixing a small merge conflict. Your job is to unblock the Worker.
**Triggers:** "pick up workflow", "continue workflow", "check status", "initiate workflow".
**Responsibilities:**
1.  **Discover State:** Check open PRs and unassigned issues (always fetch issue comments too - details alone are insufficient).
2.  **Review & Merge:** Prioritize reviewing and merging open PRs to keep the pipeline moving.
3.  **Assign Work:** Assign issues to `@copilot` based on the **Assignment Rules** below.
4.  **Report:** Summarize actions taken (PRs merged, issues assigned, blocked items).

**CRITICAL: Execute, Don't Ask.**
When a trigger phrase is used, execute the ENTIRE workflow autonomously:
- Review PRs → Approve/Merge → Assign next issues → THEN report what was done
- **NEVER** stop to ask "Would you like me to...?" or "Should I...?"
- **NEVER** generate a status report and wait for instructions
- The user does not review - YOU review. The user does not assign - YOU assign.

**CRITICAL: All Work Needs Issues.**
Even documentation changes by the Orchestrator must be tracked:
- Create a GitHub issue BEFORE making changes (or reference an existing one)
- Commit messages must reference issue numbers (`Closes #N`)
- No "drive-by" commits without issue tracking

### Copilot Coding Agent - The Worker
**Role:** Autonomous code implementer. You do not plan or manage issues. You write code to satisfy Acceptance Criteria.
**Trigger:** Assignment to a GitHub issue.
**Responsibilities:**
1.  Read the issue Context and Acceptance Criteria.
2.  Implement the solution in a new branch.
3.  Create a Pull Request.
4.  **Self-Correction:** If CI fails, fix it immediately.

## 2. Project Overview

**ComfyGen** is a programmatic image/video generation pipeline using ComfyUI. It enables text-based workflow execution, bypassing the ComfyUI GUI for automation and CI/CD integration.

**Tech Stack:** Python, ComfyUI API, MinIO (object storage), GitHub Actions.

**Key Architecture:**
- `generate.py` - Main CLI for queuing workflows to ComfyUI API
- `workflows/` - JSON workflow templates (exported from ComfyUI)
- `scripts/` - Cross-platform Python utilities for server management
- `.github/workflows/` - CI/CD automation via ant-man runner

**Data Flow:**
```
magneto (git push) --> GitHub --> ant-man (runner) --> moira (ComfyUI)
                                                          |
                                                          v
                                                     MinIO storage
                                                          |
                                                          v
                                              http://192.168.1.215:9000/comfy-gen/
```

**Infrastructure:**
| Machine | Role | IP |
|---------|------|-----|
| magneto | Development workstation | 192.168.1.124 |
| moira | ComfyUI server + MinIO + GPU (RTX 5090) | 192.168.1.215 |
| ant-man | GitHub Actions runner (ARM64) | 192.168.1.253 |

## 3. Issue-Driven Workflow
1.  **Create Issue:** Use standard template (Context, Acceptance Criteria, Notes).
2.  **Labeling:** Apply `serial-assignment`, `parallel-ok`, or `human-required`.
3.  **Assignment:** Assign to `@copilot`.
4.  **Review:** Review draft PR, request changes or merge.

## 4. Assignment Rules (Conflict Prevention)

| Label | Meaning | Rule |
|-------|---------|------|
| `serial-assignment` | Touches high-conflict files (e.g., `generate.py`, core workflows) | **ONE AT A TIME.** Wait for PR merge before assigning next. |
| `parallel-ok` | Isolated changes (e.g., new workflows, scripts, docs) | **BATCH OK.** Can assign 3-5 simultaneously. |
| `human-required` | Requires GPU access, ComfyUI runtime, model downloads | **DO NOT ASSIGN.** Report to user. |

**High-conflict files:** `generate.py`, `workflows/flux-dev.json` (base workflow)

## 5. Build & Test Commands

```bash
# Generate an image (from magneto)
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png

# Check ComfyUI server status
curl -s http://192.168.1.215:8188/system_stats | python3 -m json.tool

# Start ComfyUI server (via SSH to moira)
ssh moira "C:\\Users\\jrjen\\comfy\\.venv\\Scripts\\python.exe C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py"

# List images in MinIO
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+'

# View image directly
open "http://192.168.1.215:9000/comfy-gen/<filename>.png"
```

## 6. Code Conventions

- **CRITICAL: No PowerShell/Batch Files** - All scripts must be Python for cross-platform compatibility.
- **CRITICAL: No Emojis** - Windows cp1252 encoding breaks on Unicode. Use `[OK]`, `[WARN]`, `[ERROR]`.
- **Style:** Python with type hints. Use `sys.exit(1)` for failures.
- **File organization:** Workflows in `workflows/`, scripts in `scripts/`. NEVER create files in root except `generate.py`.

**NSFW Content Policy:**
- **NEVER** include NSFW prompts, tags, or keywords in any committed file
- **NEVER** upload NSFW images to GitHub or public locations
- NSFW content is stored ONLY in local MinIO (`comfy-gen` bucket)
- Use generic/safe example prompts in documentation and tests
- Use explicit example prompts in real world generation

## 7. Model & LoRA Management

**IMPORTANT:** All models live in ONE location: `C:\Users\jrjen\comfy\models\`

The `extra_model_paths.yaml` file (in ComfyUI directory) tells ComfyUI where to find models. It points to our unified model directory - this is NOT a separate location, it's just configuration.

**Model Registry:** See `docs/MODEL_REGISTRY.md` for complete inventory.
**Agent Guide:** See `docs/AGENT_GUIDE.md` for how to use models and LoRAs.

**Directory Structure on moira:**
```
C:\Users\jrjen\comfy\models\
├── checkpoints/      # Base models (SD 1.5, SDXL, Flux, Wan)
├── loras/            # LoRA adapters
├── vae/              # VAE models
├── text_encoders/    # T5, CLIP encoders
├── diffusion_models/ # Wan 2.2, etc.
├── unet/             # UNet models
└── sams/             # Segment Anything models
```

## 8. Image Generation Quick Reference

**For agents executing generation requests:**

1. **Read the request** - What subject? What style?
2. **Choose workflow** - SD 1.5 for images, Wan 2.2 for video
3. **Generate** - `python3 generate.py --workflow <file> --prompt "<prompt>" --output /tmp/output.png`
4. **Return URL** - Image will be at `http://192.168.1.215:9000/comfy-gen/<timestamp>_<filename>`

See `docs/AGENT_GUIDE.md` for:
- LoRA selection and strength guidelines
- Prompt engineering tips
- Error handling procedures
- Decision tree for model selection

## 9. Troubleshooting

- **Assignment Stuck:** Unassign and reassign `@copilot`.
- **Dirty Merges:** If a PR has complex conflicts, close it and reassign the issue to trigger a fresh branch.
- **Stale Branches:** If `main` changes significantly (refactor), close stale PRs and reassign.
- **ComfyUI not responding:** SSH to moira, check `tasklist | findstr python`, restart with `start_comfyui.py`.
- **Model not found:** Verify model exists in `C:\Users\jrjen\comfy\models\` and workflow references correct filename.
- **MinIO access denied:** Bucket policy may have reset. Run `scripts/set_bucket_policy.py`.
- **Image not appearing:** Check MinIO bucket at `http://192.168.1.215:9000/minio/comfy-gen/`.
