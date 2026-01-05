# Copilot & Agent Instructions

## 1. Agent Roles & Autonomous Workflow

### VS Code Agent (Claude) - The Orchestrator
**Role:** Autonomous workflow manager. You do not write application code unless fixing a small merge conflict. Your job is to unblock the Worker.
**Triggers:** "pick up workflow", "continue workflow", "check status", "initiate workflow".
**Responsibilities:**
1.  **Discover State:** Check open PRs and unassigned issues. **ALWAYS fetch issue comments** - the body alone is insufficient. Comments contain progress updates, scope changes, and blockers.
2.  **Review & Merge:** Prioritize reviewing and merging open PRs to keep the pipeline moving.
3.  **Assign Work:** Assign issues to `@copilot` based on the **Assignment Rules** below. See **Pre-Assignment Checklist** in Section 3.
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

**Meta-Issue Responsibilities:**
When assigned a meta-issue (instruction/documentation updates):
1.  Read the CURRENT version of the file being updated (don't assume you know it)
2.  Identify the specific gap or confusion mentioned in the issue
3.  Add minimal, precise guidance that addresses ONLY the stated gap
4.  Preserve existing structure and formatting
5.  Do NOT refactor unrelated sections
6.  Test documentation changes by reading them back to ensure clarity

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
2.  **Labeling:** Apply `serial-assignment`, `parallel-ok`, `local-network`, or `human-required`.
3.  **Assignment:** Assign to `@copilot` (or Orchestrator handles `local-network` directly).
4.  **Review:** Review draft PR, request changes or merge.

### Meta-Issue Handling (Instruction Updates)

**Meta-issues** are issues about the workflow itself (e.g., updating copilot-instructions.md, issue templates, workflow documentation).

**Assignment Rules for Meta-Issues:**
- **Copilot can handle:** Updates to `.github/copilot-instructions.md` when the issue has clear, specific acceptance criteria
- **Orchestrator self-assigns:** Complex workflow redesigns or when the gap is unclear and requires workflow context to diagnose
- **Either can handle:** Documentation updates (`README`, `docs/`, `examples/`)
- **Label as `parallel-ok`:** Instruction updates don't conflict with code changes

**Meta-Issue Template:**
When creating issues about instruction updates, include:
1. **Context:** What workflow gap or confusion occurred?
2. **Acceptance Criteria:** What specific section/guidance needs to be added?
3. **Example:** Reference the issue number that exposed the gap

**Example Meta-Issue:**
```
Title: Add guidance for meta-issue handling
Context: Issues about updating instructions themselves create circular dependency
Acceptance Criteria:
- [ ] Add section explaining who handles meta-issues (Orchestrator vs Copilot)
- [ ] Define "meta-issue" clearly
- [ ] Provide examples of meta-issue patterns
Example: Issue #123 exposed this gap when Copilot was unsure how to handle an issue about issue handling
```

### Pre-Assignment Checklist (MANDATORY)

**CRITICAL: Before assigning ANY issue to Copilot, you MUST complete ALL of these steps:**

1. **Read the issue body** - Understand the full scope and acceptance criteria.
2. **Read ALL issue comments** - Use `mcp_github_issue_read` with `method: get_comments`. Comments often contain:
   - Progress updates showing work is partially done
   - Blockers or scope changes
   - Context that changes what needs to be implemented
3. **Check for linked PRs** - Search for open PRs referencing this issue number.
4. **Evaluate remaining work** - If comments show 80% complete, the issue scope has narrowed. Consider:
   - Updating the issue body to reflect only remaining work
   - Adding a comment clarifying what Copilot should implement
5. **Verify label accuracy** - Does it still need `serial-assignment` if only docs remain?

**Anti-Pattern (DO NOT DO THIS):**
```
[BAD] See issue title -> Assign to Copilot -> Move on
```

**Correct Pattern:**
```
[OK] Read issue body -> Read ALL comments -> Check for PRs -> Assess remaining scope -> Update issue if needed -> THEN assign
```

**Example Failure Case:**
Issue #68 had a comment showing Phase 2 and 3 were complete, only `--prompt-preset` flag remained. Assigning without reading comments causes Copilot to redo completed work or create conflicting changes.

## 4. Assignment Rules (Conflict Prevention)

| Label | Meaning | Rule |
|-------|---------|------|
| `serial-assignment` | Code changes to high-conflict files (e.g., `generate.py`, core workflows) | **ONE AT A TIME.** Wait for PR merge before assigning next. |
| `parallel-ok` | Isolated code changes (e.g., new workflows, scripts, docs) | **BATCH OK.** Can assign 3-5 simultaneously. |
| `local-network` | Requires local network access - SSH, ComfyUI API, generation, model downloads, GPU tasks | **ORCHESTRATOR ONLY.** VS Code Agent handles directly - do NOT assign to Copilot (it runs on GitHub infra, no local network access). |
| `human-required` | Requires true human intervention (physical access, subjective aesthetic decisions, external account setup) | **DO NOT ASSIGN.** Report to user. |

**CRITICAL: Image/Video Generation is ALWAYS `local-network`**
- Generation requires ComfyUI API at `192.168.1.215:8188` (moira)
- Copilot runs on GitHub infrastructure - it CANNOT reach the local network
- Only the Orchestrator (VS Code Agent) can execute generation requests
- Label generation issues as `local-network`, NOT `serial-assignment`

**Rate Limiting Prevention:**
- Assign maximum **3 parallel-ok issues at once** to avoid token exhaustion
- Wait for at least one PR to complete before assigning more
- If rate limited, wait 1-2 hours before resuming assignments

**High-conflict files (for code changes):** `generate.py`, `workflows/flux-dev.json` (base workflow)

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
- **CRITICAL: Use Detailed, Verbose Prompts** - Models can handle paragraph-length prompts. See `docs/USAGE.md` for examples. Short prompts like "a battleship, top-down" are inadequate - use 100-200 token detailed descriptions with redundant constraint reinforcement.
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
**LoRA Catalog:** See `lora_catalog.yaml` for semantic tags and metadata.
**Usage Guide:** See `docs/USAGE.md` for CLI and MCP server usage.

**API Keys for Downloads:**
- `.env` file (gitignored) stores API keys: `CIVITAI_API_KEY`, `HF_TOKEN`
- CivitAI requires auth for many downloads
- HuggingFace required for gated models
- civitai_client.py automatically uses `CIVITAI_API_KEY` from environment

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

1. **Read the request** - What subject? What style? What constraints?
2. **Craft a DETAILED, VERBOSE prompt** - Use paragraph-length descriptions (100-200 tokens)
   - See `docs/USAGE.md` for comprehensive examples
   - Layer constraints with redundant phrasing (e.g., "top-down view, orthographic, no perspective, flat like a blueprint")
   - Include: subject, perspective, style, specific elements, what to avoid
3. **Choose workflow** - SD 1.5 for images, Wan 2.2 for video
4. **Set parameters appropriately:**
   - Steps: 30 for drafts, 80+ for final/complex prompts
   - CFG: 7.0 default, 8-10 for stricter prompt adherence
5. **Generate** - `python3 generate.py --workflow <file> --prompt "<detailed_prompt>" --negative-prompt "<detailed_negative>" --steps 80 --output /tmp/output.png`
6. **Return URL** - Image will be at `http://192.168.1.215:9000/comfy-gen/<timestamp>_<filename>`

See `docs/USAGE.md` for:
- LoRA selection and strength guidelines
- Detailed prompt engineering strategies
- Error handling procedures
- Decision tree for model selection

## 9. Troubleshooting

- **Assignment Stuck:** Unassign and reassign `@copilot` on the **issue**.
- **Dirty Merges / Stale PRs:** If a PR has merge conflicts or is stale after `main` changed, **unassign then reassign the issue** (not the PR). Copilot will create a fresh branch from updated `main`. The old PR will be superseded.
- **Rate Limited (PR Stopped):** Copilot hit token limits. Wait 1-2 hours, then unassign and reassign the issue. The PR branch may be salvageable - check if it has partial progress worth keeping.

**Unassignment Procedure (MCP Tool Workaround):**
The `mcp_github_issue_write` tool with `assignees: []` is **ignored** - it does NOT clear assignees.
The `mcp_github_assign_copilot_to_issue` tool **adds** Copilot to existing assignees (doesn't replace).

To properly reset an issue for Copilot (correct order: REMOVE first, then ADD):
```bash
# Step 1: Remove ALL assignees including Copilot
gh issue edit <N> --repo <owner>/<repo> --remove-assignee Copilot,<other_users>

# Step 2: Assign Copilot fresh (triggers new work from current main)
# Use mcp_github_assign_copilot_to_issue tool
```
- **ComfyUI not responding:** SSH to moira, check `tasklist | findstr python`, restart with `start_comfyui.py`.
- **Model not found:** Verify model exists in `C:\Users\jrjen\comfy\models\` and workflow references correct filename.
- **MinIO access denied:** Bucket policy may have reset. Run `scripts/set_bucket_policy.py`.
- **Image not appearing:** Check MinIO bucket at `http://192.168.1.215:9000/minio/comfy-gen/`.
