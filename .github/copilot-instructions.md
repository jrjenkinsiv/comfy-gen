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

**CRITICAL: Proactive Workflow Improvement.**
When you encounter a workflow gap, ambiguity, or pattern that causes repeated confusion:
1. **Create a meta-issue immediately** - Don't wait for the user to tell you
2. **Reference the triggering context** - What issue/PR/conversation exposed this gap?
3. **Propose the fix** - Include specific text to add or modify in the issue body
4. **Self-assign OR assign to Copilot** - Simple additions → Copilot; complex redesigns → self
5. **Implement the fix** - Update `copilot-instructions.md` with tracked commits

This ensures the workflow improves iteratively without repeated user intervention. If the same confusion occurs twice, create an issue to prevent a third occurrence.

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

**Meta-issues** are issues about the workflow itself (e.g., updating `copilot-instructions.md`, issue templates, workflow documentation).

**Assignment Rules for Meta-Issues:**
- **Copilot can handle:** Updates to `.github/copilot-instructions.md` when the issue has clear, specific acceptance criteria
  - Example: "Add section on X with template Y and example Z"
- **Orchestrator self-assigns:** Complex workflow redesigns or when the gap is unclear and requires workflow context to diagnose
  - Example: "Workflow feels unclear" (needs investigation to identify specific gap)
- **Either can handle:** Documentation updates (`README.md`, `docs/`, `examples/`)
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
| `simple-task` | Simple/straightforward work (docs, config, file moves, simple refactors) | **LOCAL MODEL.** Orchestrator handles with free/cheap model (GPT-5 Mini) - saves Copilot tokens for complex work. |
| `local-network` | Requires local network access - SSH, ComfyUI API, generation, model downloads, GPU tasks | **ORCHESTRATOR ONLY.** VS Code Agent handles directly - do NOT assign to Copilot (it runs on GitHub infra, no local network access). |
| `human-required` | Requires true human intervention (physical access, subjective aesthetic decisions, external account setup) | **DO NOT ASSIGN.** Report to user. |

### Complexity Assessment (Before Assignment)

**Ask:** "Is this simple enough for a local free model?"

| Complexity | Examples | Route To |
|------------|----------|----------|
| **Simple** | Doc updates, file moves, config changes, simple scripts | Local model (`simple-task`) |
| **Medium** | New modules, refactors, API integrations | Copilot (`parallel-ok`) |
| **Complex** | Core system changes, multi-file refactors | Copilot (`serial-assignment`) |
| **Network** | SSH, generation, GPU tasks | Orchestrator (`local-network`) |

**Cost-aware routing:** Use Copilot tokens for complex code generation, not documentation.

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
   - Steps: 50-70 for quality, 30 for quick drafts
   - CFG: 8.5-9.5 for NSFW/explicit (stricter adherence), 7.0-8.0 for general
5. **Generate** - `python3 generate.py --workflow <file> --prompt "<detailed_prompt>" --negative-prompt "<detailed_negative>" --steps 70 --cfg 9.0 --output /tmp/output.png`
6. **Return URL** - Image will be at `http://192.168.1.215:9000/comfy-gen/<timestamp>_<filename>`

### CRITICAL: Video vs Image LoRAs

**NEVER use Wan 2.2 video LoRAs for SD 1.5 image generation.**

**How to verify LoRA compatibility - Use CivitAI `baseModel`, NOT file size!**

The authoritative source for LoRA base model is CivitAI API. Use `scripts/civitai_audit.py` to verify, or:

```bash
# 1. Get SHA256 hash from moira
ssh moira "powershell -Command \"(Get-FileHash -Algorithm SHA256 '<path>').Hash\""

# 2. Look up on CivitAI API - returns baseModel, trainedWords
curl "https://civitai.com/api/v1/model-versions/by-hash/<SHA256_HASH>"
```

**Base Model Categories:**
| Base Model | Use For | Example Files |
|------------|---------|---------------|
| `SD 1.5` | Image generation | `airoticart_penis.safetensors`, `polyhedron_skin.safetensors` |
| `Wan Video 14B t2v/i2v` | Video generation ONLY | `erect_penis_epoch_80.safetensors`, `deepthroat_epoch_80.safetensors` |

**Verified SD 1.5 Image LoRAs (CivitAI Confirmed):**
- `airoticart_penis.safetensors` - SD 1.5, triggers: `penerec` (erect), `penflac` (flaccid)
- `polyhedron_skin.safetensors` - SD 1.5, triggers: `detailed skin`
- `realora_skin.safetensors` - SD 1.5, no triggers needed

**Verified Wan Video LoRAs (DO NOT use for images):**
- `erect_penis_epoch_80.safetensors` - Wan Video 14B t2v
- `deepthroat_epoch_80.safetensors` - Wan Video 14B t2v
- `big_breasts_v2_epoch_30.safetensors` - Wan Video 14B t2v
- `doggyPOV_v1_1.safetensors` - Wan Video 14B i2v
- Any file with `wan`, `WAN`, `i2v`, `t2v` in name

**See `docs/LORA_GUIDE.md` for complete LoRA selection guide.**
**See `lora_catalog.yaml` for full inventory with CivitAI verification status.**

See `docs/USAGE.md` for:
- LoRA selection and strength guidelines
- Detailed prompt engineering strategies
- Error handling procedures
- Decision tree for model selection

## 9. Copilot Assignment & Unassignment

**CRITICAL:** Copilot is a BOT account (`BOT_kgDOC9w8XQ`). Standard CLI commands do NOT work for BOT accounts. You MUST use **GraphQL mutations**.

### Key IDs
- **Copilot BOT ID:** `BOT_kgDOC9w8XQ` (constant across all repos)
- **Issue Node ID:** Must be fetched per-issue (see below)

### Step 1: Get Issue Node ID

```bash
gh api graphql -f query='
query {
  repository(owner: "jrjenkinsiv", name: "comfy-gen") {
    issue(number: <N>) {
      id
      assignees(first: 5) { nodes { login, id } }
    }
  }
}'
```

### Step 2: Assign Copilot (Triggers Agent)

```bash
gh api graphql -f query='
mutation {
  addAssigneesToAssignable(input: {
    assignableId: "<ISSUE_NODE_ID>"
    assigneeIds: ["BOT_kgDOC9w8XQ"]
  }) {
    assignable {
      ... on Issue { assignees(first: 5) { nodes { login } } }
    }
  }
}'
```

### Step 3: Unassign Copilot

```bash
gh api graphql -f query='
mutation {
  removeAssigneesFromAssignable(input: {
    assignableId: "<ISSUE_NODE_ID>"
    assigneeIds: ["BOT_kgDOC9w8XQ"]
  }) {
    assignable {
      ... on Issue { assignees(first: 5) { nodes { login } } }
    }
  }
}'
```

### What Does NOT Work (BOT accounts)

| Method | Assign | Unassign | Triggers Agent |
|--------|--------|----------|----------------|
| `gh issue edit --add-assignee Copilot` | ❌ | ❌ | ❌ |
| `gh issue edit --remove-assignee Copilot` | N/A | ❌ | N/A |
| REST API POST/DELETE | ❌ | ❌ | ❌ |
| `mcp_github_assign_copilot_to_issue` | ❌ (bug) | N/A | ❌ |
| **GraphQL mutation** | ✅ | ✅ | ✅ |

### Reset/Reassign Procedure

When Copilot is stuck, rate-limited, or a PR has conflicts:

```bash
# 1. Get issue node ID
gh api graphql -f query='query { repository(owner: "jrjenkinsiv", name: "comfy-gen") { issue(number: <N>) { id } } }'

# 2. Unassign via GraphQL (use the id from step 1)
gh api graphql -f query='mutation { removeAssigneesFromAssignable(input: { assignableId: "<ID>", assigneeIds: ["BOT_kgDOC9w8XQ"] }) { assignable { ... on Issue { assignees(first:5) { nodes { login } } } } } }'

# 3. Reassign via GraphQL (triggers fresh work from current main)
gh api graphql -f query='mutation { addAssigneesToAssignable(input: { assignableId: "<ID>", assigneeIds: ["BOT_kgDOC9w8XQ"] }) { assignable { ... on Issue { assignees(first:5) { nodes { login } } } } } }'
```

### Verification

After assigning, a PR should appear within 30-60 seconds:
```bash
gh pr list --state open --json number,title,createdAt
```

## 10. Troubleshooting

- **Assignment Stuck:** Use GraphQL reset procedure in Section 9 (unassign then reassign via GraphQL mutations).
- **Dirty Merges / Stale PRs:** Unassign then reassign the **issue** via GraphQL. Copilot will create a fresh branch.
- **Rate Limited (PR Stopped):** Wait 1-2 hours, then use GraphQL reset procedure.
- **MCP Tool `mcp_github_assign_copilot_to_issue` Fails:** Known bug - use GraphQL mutations instead.
- **ComfyUI not responding:** SSH to moira, check `tasklist | findstr python`, restart with `start_comfyui.py`.
- **Model not found:** Verify model exists in `C:\Users\jrjen\comfy\models\` and workflow references correct filename.
- **MinIO access denied:** Bucket policy may have reset. Run `scripts/set_bucket_policy.py`.
- **Image not appearing:** Check MinIO bucket at `http://192.168.1.215:9000/minio/comfy-gen/`.

## 11. Workflow Pickup Procedure

**Trigger phrases:** "pick up workflow", "continue workflow", "check status", "resume", "initiate workflow"

**When triggered, execute these steps IN ORDER (autonomously, without asking):**

### Step 1: Discover State

Check the current state of PRs and issues:

```bash
# Check open PRs
gh pr list --repo jrjenkinsiv/comfy-gen --state open --json number,title,createdAt,headRefName,isDraft

# Check open issues (unassigned or assigned to Copilot)
gh issue list --repo jrjenkinsiv/comfy-gen --state open --json number,title,labels,assignees
```

**Analysis:**
- Identify PRs ready for review (non-draft, CI passing)
- Identify issues that need assignment (no assignee or assigned to Copilot)
- Note any `local-network` or `human-required` items

### Step 2: Review & Merge PRs (Priority)

**CRITICAL:** Clear the PR queue first to unblock the pipeline.

For each open PR:
1. Read PR description and diff
2. Check CI status: `gh pr checks <PR_NUMBER>`
3. **If CI passing and code looks good:**
   ```bash
   gh pr review <PR_NUMBER> --approve --body "LGTM - CI passing, changes verified"
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```
4. **If CI failing:**
   - Read error logs
   - If fixable by Copilot → Add review comment requesting fix
   - If needs reset → Use GraphQL reset procedure (Section 9)
5. **If conflicts or stale:**
   - Unassign and reassign the linked issue (Section 9) to trigger fresh branch

### Step 3: Identify Assignable Issues

Filter issues by label type:

**Assign to Copilot:**
- `serial-assignment` - ONE AT A TIME (wait for PR merge before next)
- `parallel-ok` - Batch 3-5 simultaneously

**Handle Directly (Orchestrator):**
- `local-network` - Requires local network access (SSH, ComfyUI API, generation)

**Report to User:**
- `human-required` - Needs true human intervention

**Skip:**
- Already assigned to Copilot with open PR
- Already assigned to user

### Step 4: Pre-Assignment Checklist (MANDATORY)

**Before assigning ANY issue, complete ALL steps from Section 3:**

1. **Read issue body** - Full scope and acceptance criteria
2. **Read ALL comments:**
   ```bash
   # Use GitHub MCP tool if available, or:
   gh issue view <ISSUE_NUMBER> --json number,title,body,comments --jq '.comments[].body'
   ```
3. **Check for linked PRs:**
   ```bash
   gh pr list --search "fixes #<ISSUE_NUMBER>" --state all
   ```
4. **Evaluate remaining scope** - Update issue if needed
5. **Verify label accuracy** - Still `serial-assignment` or now `parallel-ok`?

### Step 5: Assign to Copilot

Use GraphQL mutation (Section 9):

```bash
# 1. Get issue node ID
ISSUE_ID=$(gh api graphql -f query='
query {
  repository(owner: "jrjenkinsiv", name: "comfy-gen") {
    issue(number: <N>) {
      id
    }
  }
}' --jq '.data.repository.issue.id')

# 2. Assign via GraphQL
gh api graphql -f query="
mutation {
  addAssigneesToAssignable(input: {
    assignableId: \"$ISSUE_ID\"
    assigneeIds: [\"BOT_kgDOC9w8XQ\"]
  }) {
    assignable {
      ... on Issue { assignees(first: 5) { nodes { login } } }
    }
  }
}"

# 3. Verify PR appears within 60 seconds
sleep 60
gh pr list --state open --json number,title,createdAt
```

**Rate Limiting:**
- Maximum 3 `parallel-ok` issues at once
- Wait for at least 1 PR to complete before assigning more

### Step 6: Report Actions Taken

Provide a summary of:
- **PRs merged:** Count and issue numbers closed
- **Issues assigned:** Issue numbers and labels
- **Local-network items:** Actions taken by Orchestrator
- **Blocked items:** `human-required` issues waiting for user

**Example Report:**
```
Workflow pickup complete:
- Merged PRs: #45, #46 (CI passing)
- Assigned to Copilot: #47 (serial-assignment), #48 (parallel-ok)
- Handled directly: #49 (local-network - image generation completed)
- Awaiting user: #50 (human-required - CivitAI account setup)
```

### Decision Tree

```
Trigger phrase detected
    |
    v
[Step 1] Discover state (PRs, issues)
    |
    v
[Step 2] Any open PRs?
    |-- Yes --> Review each PR
    |           |-- CI passing? --> Approve & merge
    |           |-- CI failing? --> Request fix or reset
    |           |-- Conflicts? --> Unassign/reassign issue
    |
    v
[Step 3] Filter issues by label
    |-- serial-assignment --> Check if any already assigned
    |                         |-- None assigned? --> Proceed to Step 4
    |                         |-- One assigned? --> Wait for merge
    |
    |-- parallel-ok --> Check count already assigned
    |                   |-- <3 assigned? --> Proceed to Step 4
    |                   |-- >=3 assigned? --> Wait for completion
    |
    |-- local-network --> Handle directly (Orchestrator)
    |
    |-- human-required --> Report to user
    |
    v
[Step 4] Pre-assignment checklist (Section 3)
    |-- Read body, comments, check PRs
    |-- Evaluate remaining scope
    |
    v
[Step 5] Assign via GraphQL (Section 9)
    |
    v
[Step 6] Report summary to user
```

## 12. Infrastructure Placement Guidelines

**Before creating a new service, ask: "Which machine fits this role?"**

### Service Placement Decision Tree

When building new services, be intentional about placement to avoid later migrations:

| Machine | Primary Role | Deploy Here If... | Do NOT Deploy If... |
|---------|--------------|-------------------|---------------------|
| **magneto** | Development workstation | - Development tools only<br>- Short-lived testing scripts<br>- One-off experiments | - Long-running services<br>- Production workloads<br>- Persistent databases<br>- Public-facing services |
| **cerebro** | Monitoring & persistent services | - Monitoring dashboards<br>- Metrics collection<br>- Persistent databases (PostgreSQL)<br>- Web UIs for browsing/analytics<br>- MLflow tracking server<br>- Gallery server | - GPU workloads<br>- Heavy compute tasks<br>- CI/CD runners<br>- Development experiments |
| **moira** | GPU workloads & storage | - ComfyUI server<br>- Model training<br>- Image/video generation<br>- MinIO object storage<br>- GPU-accelerated tasks | - Monitoring tools<br>- CI/CD runners<br>- Non-GPU web services |
| **ant-man** | CI/CD only | - GitHub Actions runner<br>- CI pipeline tasks | - Persistent services<br>- Manual workloads<br>- User-facing services<br>- Anything requiring local network access from outside CI |

### Quick Reference: Current Services by Machine

| Machine | IP | Currently Running Services |
|---------|-----|---------------------------|
| **magneto** | 192.168.1.124 | Development workstation (VS Code, git, local testing) |
| **cerebro** | *(not in infra table)* | Gallery server, PostgreSQL, MLflow, monitoring dashboards |
| **moira** | 192.168.1.215 | ComfyUI server (`:8188`), MinIO (`:9000`), GPU tasks (RTX 5090) |
| **ant-man** | 192.168.1.253 | GitHub Actions runner (ARM64) |

### Decision Checklist for New Services

Before implementing a new service, answer these questions:

1. **Does it need GPU access?** → moira
2. **Is it a persistent monitoring/analytics tool?** → cerebro
3. **Is it part of CI/CD automation?** → ant-man
4. **Is it temporary development tooling?** → magneto (but consider if it should be elsewhere)

**Example Migration Pattern (Anti-Pattern):**
- Issue jrjenkinsiv/comfy-gen#96: Gallery server was initially placed on magneto (dev workstation) but belonged on cerebro (persistent services). This required manual migration.
- **Lesson:** Long-running web services with persistent state → cerebro, NOT magneto.

**When in doubt:** Default to cerebro for web services, moira for GPU/storage tasks.
