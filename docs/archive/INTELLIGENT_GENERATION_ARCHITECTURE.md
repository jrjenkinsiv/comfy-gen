# Intelligent Generation System Architecture

## Vision

Transform comfy-gen from a CLI/MCP generation tool into an **intelligent, composable generation system** that:

1. **Understands natural language requests** and maps them to optimal generation settings
2. **Maintains category knowledge** (cars, anime, people, cities, NSFW, etc.) with best practices per category
3. **Composes presets intelligently** when categories combine ("person driving car in city")
4. **Learns from favorites** - reuse successful generation parameters across subjects
5. **Provides explicit tagging** (`@car @city`) for precision when natural language is ambiguous

## Core Concepts

### 1. Categories (Domains)

A **Category** is a domain of expertise with associated best practices:

```yaml
categories:
  car:
    display_name: "Vehicles & Automotive"
    description: "Cars, trucks, motorcycles, and automotive content"
    
    # Prompt fragments to inject
    prompt_fragments:
      positive:
        - "professional automotive photography"
        - "studio lighting reflections"
        - "clean lines"
      negative:
        - "duplicate cars, multiple vehicles, car show, parking lot"
    
    # LoRAs that enhance this category
    recommended_loras:
      - filename: "car_detail_lora.safetensors"
        strength: 0.6
    
    # Quality settings optimized for this category
    settings:
      cfg: 7.5
      sampler: dpmpp_2m_sde
      steps: 50
    
    # Compatible workflows
    workflows:
      image: ["flux-dev.json", "realistic-vision.json"]
      video: ["wan22-t2v.json"]
    
    # Tags for matching (NL understanding)
    keywords: ["car", "vehicle", "automotive", "drive", "driving", "road"]
    
    # Composability rules
    composition:
      stacks_with: ["city", "person", "landscape", "night"]
      conflicts_with: ["underwater", "space"]
      priority: "subject"  # subject, setting, modifier
```

### 2. Category Types

Categories fall into three composition types:

| Type | Examples | Role in Composition |
|------|----------|---------------------|
| **Subject** | car, person, animal, product | The main focus - only one primary subject |
| **Setting** | city, beach, forest, studio | Where it takes place - can combine |
| **Modifier** | night, golden-hour, rainy, foggy | Atmospheric conditions - can stack |
| **Style** | anime, photorealistic, cinematic | Rendering style - usually exclusive |

### 3. Composition Engine

When user requests "person driving car in rainy city at night":

1. **Parse categories**: `person` (subject), `car` (subject), `city` (setting), `rainy` (modifier), `night` (modifier)
2. **Resolve conflicts**: Two subjects → combine as "person with car" (person primary, car secondary)
3. **Merge prompt fragments**: Combine positive/negative from all categories
4. **Stack LoRAs**: Include LoRAs from all compatible categories (respect limits)
5. **Select workflow**: Find workflow compatible with all categories
6. **Apply settings**: Use weighted average or category priority for settings

### 4. Favorites Learning System

```yaml
# When user marks image as favorite, we save:
favorites:
  - id: "fav_001"
    source_image: "http://192.168.1.215:9000/comfy-gen/20260104_160118.png"
    categories_used: ["person", "beach", "sunset"]
    
    # The complete recipe that worked
    recipe:
      checkpoint: "realisticVisionV60B1_v51HyperVAE.safetensors"
      workflow: "realistic-vision.json"
      loras:
        - "more_details.safetensors:0.5"
        - "skin_texture.safetensors:0.4"
      settings:
        steps: 150
        cfg: 11.0
        sampler: dpmpp_sde
        scheduler: karras
      prompt_style: "verbose"  # or "short+lora"
      
    # Extracted patterns for reuse
    transferable_elements:
      lighting_approach: "golden hour with rim lighting"
      composition: "subject isolation, centered"
      quality_boosters: ["8K resolution", "sharp focus", "detailed skin"]
```

**Reuse Flow:**
- User: "Generate a car using my beach sunset settings"
- System: Apply `fav_001` recipe but substitute `car` category for `person`

## Interface Modes

### 1. Natural Language Mode (Default)

```
User: "Generate a sports car on a rainy Tokyo street at night"

System parses:
  - Subject: sports car → @car category
  - Setting: Tokyo street → @city + @japan modifiers  
  - Modifiers: rainy, night → @rainy @night
  
System generates with merged presets.
```

### 2. Explicit Tag Mode

For precision, user can explicitly tag categories:

```
User: "@car @city @night red ferrari on wet streets"

System uses exact categories specified, no NL parsing ambiguity.
```

### 3. Preset Mode

Reference saved presets or favorites:

```
User: "Use my 'best_car_shots' preset for a Porsche 911"
User: "Apply favorite #fav_001 settings to a forest scene"
```

### 4. Builder Mode (Web UI)

Visual category composition interface (FastAPI + vanilla HTML/CSS/JS):

```
┌─────────────────────────────────────────────────────────────┐
│ ComfyGen - Intelligent Generation                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Subject:     [ 🚗 car ] [ 👤 person ] [ 🐕 animal ]        │
│               ─────────                                     │
│                                                             │
│  Setting:     [ 🏙️ city ] [ 🏖️ beach ] [ 🌲 forest ]       │
│               ────────                                      │
│                                                             │
│  Style:       [ 📷 photorealistic ] [ 🎨 anime ]           │
│               ──────────────────                            │
│                                                             │
│  Time:        [ ☀️ day ] [ 🌅 golden-hour ] [ 🌙 night ]   │
│                                     ───────                 │
│                                                             │
│  Weather:     [ ☁️ clear ] [ 🌧️ rainy ] [ 🌫️ foggy ]      │
│                          ────────                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Merged Preview:                                     │   │
│  │                                                     │   │
│  │ Checkpoint: pornmasterProPony_realismV1             │   │
│  │ LoRAs: add_detail:0.4, more_details:0.3 (+2 more)  │   │
│  │ Workflow: pornmaster-pony-stacked-realism.json      │   │
│  │ Steps: 70 | CFG: 9.0 | Sampler: euler_ancestral    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Preview Full Prompt] [💾 Save Preset] [🎨 Generate]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Categories highlight when selected, show visual icons, and update the preview in real-time.

## System Architecture

### Layer Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│                                                                 │
│   ┌─────────┐       ┌─────────┐       ┌─────────────────────┐  │
│   │   CLI   │       │   MCP   │       │        GUI          │  │
│   │ (Click) │       │ Server  │       │ (FastAPI + HTML/JS) │  │
│   └────┬────┘       └────┬────┘       └──────────┬──────────┘  │
│        │                 │                       │              │
│        └────────────────┬┴───────────────────────┘              │
│                         │                                       │
│                         ▼                                       │
├─────────────────────────────────────────────────────────────────┤
│                        API LAYER                                │
│                    (FastAPI - Core)                             │
│                                                                 │
│   /api/v1/generate      - Queue generation (returns ID fast)   │
│   /api/v1/generate/{id} - Poll status or get result            │
│   /api/v1/generate/{id}/ws - WebSocket progress stream         │
│   /api/v1/categories    - List/get category definitions        │
│   /api/v1/compose       - Preview recipe + explanation         │
│   /api/v1/favorites     - CRUD favorites                       │
│   /api/v1/presets       - Manage saved presets                 │
│   /api/v1/models        - Available checkpoints/LoRAs          │
│   /api/v1/workflows     - List/validate workflow manifests     │
│   /api/v1/policy        - Content policy configuration         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      SERVICE LAYER                              │
│                  (Business Logic - Python)                      │
│                                                                 │
│   ┌────────────┐  ┌─────────────┐  ┌───────────────────────┐   │
│   │ Categories │  │ Composition │  │      Favorites        │   │
│   │  Registry  │  │   Engine    │  │   (MLflow storage)    │   │
│   └────────────┘  └─────────────┘  └───────────────────────┘   │
│                                                                 │
│   ┌────────────┐  ┌─────────────┐  ┌───────────────────────┐   │
│   │   Recipe   │  │ NL/Tag      │  │     Generation        │   │
│   │  Builder   │  │ Parser      │  │     Pipeline          │   │
│   └────────────┘  └─────────────┘  └───────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     INTEGRATION LAYER                           │
│                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐  │
│   │  ComfyUI    │  │   MinIO     │  │       MLflow          │  │
│   │    API      │  │  Storage    │  │     (cerebro)         │  │
│   │  (moira)    │  │  (moira)    │  │                       │  │
│   └─────────────┘  └─────────────┘  └───────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **API is the single source of truth** - ALL business logic lives in the API layer
2. **Presentation layers are thin** - CLI, MCP, and GUI are just different interfaces to the same API
3. **No duplicate logic** - CLI doesn't reimplement what MCP does; both call the API
4. **API-first development** - Build API endpoints first, then wire up interfaces
5. **Explainability by default** - Every output includes a justification tree
6. **Recipe + Explanation** - System produces two outputs: a deterministic replayable recipe AND an explanation of why

### Typed Client Generation

FastAPI's automatic OpenAPI schema generation becomes a major accelerator. Generate a typed Python client that CLI and MCP share:

```python
# comfy_gen/client.py - Auto-generated from OpenAPI schema
from comfy_gen.api.schemas import GenerationRequest, GenerationResponse, ComposeResponse

class ComfyGenClient:
    """Typed HTTP client for comfy-gen API. Shared by CLI and MCP."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """POST /api/v1/generate with full type safety."""
        ...
    
    def compose(self, categories: list[str], subject: str) -> ComposeResponse:
        """POST /api/v1/compose - returns recipe + explanation."""
        ...
    
    def get_generation_status(self, generation_id: str) -> GenerationStatus:
        """GET /api/v1/generate/{id} - poll for completion."""
        ...
```

**Benefits:**
- CLI and MCP share identical request/response models
- Type errors caught at development time
- Error handling consistent across all interfaces
- OpenAPI docs (`/docs`) become interactive testing UI

### Async Execution Model

ComfyUI's architecture is queue-based with WebSocket progress updates. Our API mirrors this pattern:

```
POST /api/v1/generate          →  Returns generation_id immediately
GET  /api/v1/generate/{id}     →  Poll for status/completion
WS   /api/v1/generate/{id}/ws  →  Stream real-time progress (optional)
```

**Implementation using FastAPI BackgroundTasks:**

```python
from fastapi import BackgroundTasks

@router.post("/generate")
async def generate(
    request: GenerationRequest,
    background_tasks: BackgroundTasks
) -> GenerationResponse:
    """Enqueue generation and return immediately."""
    generation_id = str(uuid.uuid4())
    
    # Return fast, do work in background
    background_tasks.add_task(
        execute_generation,
        generation_id=generation_id,
        request=request
    )
    
    return GenerationResponse(
        generation_id=generation_id,
        status="queued",
        message="Generation queued. Poll /generate/{id} or connect to WebSocket."
    )
```

**ComfyUI WebSocket Integration:**

ComfyUI provides real-time progress via `/ws` endpoint with message types:
- `status` - System status updates
- `execution_start` - Prompt execution begins
- `progress` - KSampler step progress (e.g., "Step 15 of 50")
- `executing` - Current node being processed
- `executed` - Node completion

Our API can proxy these updates to clients for real-time feedback.

### Directory Structure

```
comfy_gen/
├── api/                    # CORE LAYER - FastAPI application
│   ├── __init__.py
│   ├── app.py              # FastAPI app initialization
│   ├── config.py           # API configuration
│   ├── websocket.py        # WebSocket progress proxy from ComfyUI
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── generation.py   # POST /generate, GET /generate/{id}, WS progress
│   │   ├── categories.py   # GET /categories, GET /categories/{id}
│   │   ├── compose.py      # POST /compose (recipe + explanation)
│   │   ├── favorites.py    # CRUD /favorites
│   │   ├── presets.py      # CRUD /presets
│   │   ├── models.py       # GET /models, /loras, /workflows
│   │   ├── policy.py       # GET/PUT /policy (content policy config)
│   │   └── health.py       # GET /health
│   └── schemas/
│       ├── __init__.py
│       ├── generation.py   # Request/response models
│       ├── category.py
│       ├── recipe.py
│       └── explanation.py  # ExplanationBlock, DriftReport
│
├── client.py               # TYPED CLIENT - Auto-generated from OpenAPI
│
├── services/               # BUSINESS LOGIC LAYER
│   ├── __init__.py
│   ├── categories/
│   │   ├── __init__.py
│   │   ├── base.py         # Category base class
│   │   ├── registry.py     # Load and manage categories (with schema validation)
│   │   ├── composition.py  # Merge categories into recipes
│   │   └── versioning.py   # Schema version + migration hooks
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── nl_parser.py    # Natural language → categories
│   │   ├── tag_parser.py   # @tag syntax parser
│   │   └── intent.py       # User intent classification
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── pipeline.py     # Orchestrate full generation
│   │   ├── recipe.py       # Build recipe from composed categories
│   │   └── executor.py     # Send to ComfyUI API
│   ├── policy/
│   │   ├── __init__.py
│   │   ├── content_policy.py  # Category gating, model allowlists
│   │   └── lora_policy.py     # LoRA caps, ordering, strategy selection
│   ├── favorites/
│   │   ├── __init__.py
│   │   ├── storage.py      # MLflow integration with provenance
│   │   ├── transfer.py     # Apply favorites to new subjects
│   │   ├── drift.py        # Category YAML drift detection
│   │   └── learning.py     # Pattern extraction
│   └── workflows/
│       ├── __init__.py
│       ├── manifests.py    # Load workflow capability manifests
│       └── selector.py     # Constraint satisfaction + scoring
│
├── categories/             # CATEGORY DEFINITIONS (YAML)
│   ├── schema_version.yaml # Version + migration definitions
│   ├── schema.json         # JSON Schema for validation
│   ├── subjects/
│   │   ├── car.yaml
│   │   ├── person.yaml
│   │   └── animal.yaml
│   ├── settings/
│   │   ├── city.yaml
│   │   ├── beach.yaml
│   │   └── forest.yaml
│   ├── modifiers/
│   │   ├── time_of_day.yaml
│   │   └── weather.yaml
│   └── styles/
│       ├── photorealistic.yaml
│       └── anime.yaml
│
├── workflows/              # WORKFLOW MANIFESTS
│   └── manifests/
│       ├── flux-dev.yaml   # Capability manifest for flux-dev.json
│       └── pony-realism.yaml
│
├── config/                 # CONFIGURATION FILES
│   ├── policy.yaml         # Content policy tiers
│   └── lora_policy.yaml    # LoRA stacking rules
│
├── cli/                    # CLICK CLI - Thin wrapper (uses client.py)
│   ├── __init__.py
│   └── main.py             # Click commands that call API via typed client
│
├── mcp/                    # MCP SERVER - Thin wrapper (uses client.py)
│   ├── __init__.py
│   └── server.py           # MCP tools that call API via typed client
│
└── ui/                     # WEB GUI - Thin wrapper
    └── frontend/
        └── public/
            ├── index.html  # Single-page app
            ├── styles.css
            └── app.js      # Calls API endpoints
```

### Interface Comparison

All three interfaces call the same API:

| Action | CLI | MCP | GUI |
|--------|-----|-----|-----|
| Generate image | `comfygen generate "@car @night"` | `generate(categories=["car","night"])` | POST `/api/v1/generate` |
| List categories | `comfygen categories list` | `list_categories()` | GET `/api/v1/categories` |
| Preview recipe | `comfygen compose "@car @city"` | `compose(categories=[...])` | POST `/api/v1/compose` |
| Save favorite | `comfygen favorite add <url>` | `save_favorite(url, rating)` | POST `/api/v1/favorites` |

### Data Flow

```
User Input (CLI, MCP, or GUI)
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│   CLI (Click)  │  MCP Server  │  Web GUI (HTML/JS)          │
│       │               │                │                     │
│       └───────────────┴────────────────┘                     │
│                       │                                      │
│              HTTP Request to API                             │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                     │
│                                                              │
│  POST /api/v1/generate                                       │
│  {                                                           │
│    "input": "@car @city @night red ferrari on wet streets", │
│    "mode": "auto"  // or "tags", "nl", "preset"             │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│                                                              │
│  ┌─────────────────┐                                         │
│  │ Intent Parser   │ Identifies: generation, query, etc.    │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │ Category Parser │ Extracts: [car, city, night]           │
│  │ (NL or @tag)    │                                        │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │ Composition     │ Merges category presets                │
│  │ Engine          │ Resolves conflicts                     │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │ Recipe Builder  │ Creates final recipe:                  │
│  │                 │ - Merged prompt                        │
│  │                 │ - LoRA stack                           │
│  │                 │ - Workflow + settings                  │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │ Executor        │ Sends to ComfyUI API                   │
│  └─────────────────┘                                         │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                  INTEGRATION LAYER                           │
│                                                              │
│  ComfyUI (moira:8188)  │  MinIO (moira:9000)  │  MLflow     │
│        │                       │                    │        │
│        ▼                       ▼                    ▼        │
│   Generate Image         Store Image         Log Metadata   │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                    RESPONSE                                  │
│                                                              │
│  {                                                           │
│    "generation_id": "gen_abc123",                           │
│    "status": "completed",                                    │
│    "image_url": "http://192.168.1.215:9000/comfy-gen/...",  │
│    "recipe": { ... },                                        │
│    "categories_used": ["car", "city", "night"],             │
│    "explanation": {                                          │
│      "matched_categories": [                                 │
│        {"id": "car", "matched_by": ["ferrari", "sports"]}, │
│        {"id": "city", "matched_by": ["Tokyo", "street"]},  │
│        {"id": "night", "matched_by": ["night"]}            │
│      ],                                                      │
│      "conflict_resolutions": [],                             │
│      "prompt_ordering": "subject → setting → modifier",     │
│      "lora_selection": [                                     │
│        {"file": "more_details.safetensors", "reason": "..."}│
│      ],                                                      │
│      "workflow_selection": {                                 │
│        "chosen": "flux-dev.json",                           │
│        "reason": "intersection of car + city preferences"   │
│      }                                                       │
│    }                                                         │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
```

### Explainability (Debugging Superpower)

The `/compose` endpoint returns a structured "explain" block that justifies every decision:

```python
class ExplanationBlock(BaseModel):
    """Justification tree for composition decisions."""
    
    matched_categories: list[CategoryMatch]  # Which categories matched and why
    conflict_resolutions: list[ConflictResolution]  # How conflicts were resolved
    prompt_ordering_rationale: str  # Why this order (subject → setting → modifier → style)
    lora_selection: list[LoRASelection]  # Why each LoRA was included
    lora_caps_applied: bool  # Did we hit the LoRA limit?
    workflow_selection: WorkflowSelection  # Why this workflow was chosen
    settings_source: dict[str, str]  # Which category each setting came from

class ComposeResponse(BaseModel):
    recipe: Recipe  # The deterministic, replayable recipe
    explanation: ExplanationBlock  # The justification tree
```

**When users ask "why did it pick that workflow / sampler / LoRA," point at the explanation.**

### Workflow Capability Manifests

Instead of simple list intersection for workflow selection, use constraint-based manifests:

```yaml
# workflows/manifests/flux-dev.yaml
workflow:
  id: "flux-dev"
  file: "flux-dev.json"
  
  # Hard constraints
  constraints:
    modality: "image"  # image | video
    base_model_family: ["flux", "sdxl"]  # Compatible base models
    required_nodes: ["KSampler", "CLIPTextEncode"]
    conditioning_types: ["text", "image"]  # What inputs it accepts
    max_lora_count: 4  # Hard cap for this workflow
    
  # Soft preferences (for scoring)
  best_for:
    - "photorealistic"
    - "high-detail"
    - "automotive"
  
  # Capability flags
  capabilities:
    supports_controlnet: true
    supports_img2img: true
    supports_inpainting: false
    supports_lora_switch: false  # Needs custom workflow variant
```

**Selection becomes constraint satisfaction + scoring:**
1. Filter workflows by hard constraints (modality, base model, required nodes)
2. Score remaining by soft preferences (category alignment)
3. Return best match with explanation of why

**Empty intersection handling:** If no workflow satisfies all constraints, return error with specific constraint that failed.

## Implementation Phases

### Phase 0: API Foundation (Do This First)
- [ ] Create FastAPI app skeleton in `comfy_gen/api/`
- [ ] Define core schemas (GenerationRequest, Recipe, Category, ExplanationBlock)
- [ ] Implement `/health` and `/api/v1/models` endpoints
- [ ] Port existing `generate.py` logic to API service layer
- [ ] Wire up basic `/api/v1/generate` endpoint (async pattern: returns ID, background execution)
- [ ] Implement `/api/v1/generate/{id}` polling endpoint
- [ ] Generate typed Python client from OpenAPI schema
- [ ] Add WebSocket progress proxy from ComfyUI

### Phase 1: Category System Foundation
- [ ] Define Category data model and YAML schema with **strict versioning**
- [ ] Implement JSON Schema validation at load time (fail-fast with friendly errors)
- [ ] Create category registry and loader with migration hooks (v1 → v2 transforms)
- [ ] Define initial categories (5-10 core categories)
- [ ] Basic composition engine (merge fragments, stack LoRAs)
- [ ] Add `/api/v1/categories` endpoints
- [ ] Implement workflow manifest system with constraint satisfaction

### Phase 2: Parsing & Intent
- [ ] Implement @tag parser for explicit mode
- [ ] Implement NL parser using keyword matching (v1)
- [ ] Intent classification (generate vs query vs settings)
- [ ] Add `/api/v1/compose` endpoint with **ExplanationBlock** (recipe + justification)
- [ ] Implement content policy layer (category allow/deny gating)

### Phase 3: CLI Migration
- [ ] Create new Click CLI in `comfy_gen/cli/`
- [ ] CLI calls API endpoints (not direct logic)
- [ ] Migrate existing `generate.py` commands to new CLI
- [ ] Deprecate old `generate.py` entrypoint

### Phase 4: MCP Migration
- [ ] Refactor `mcp_server.py` to call API
- [ ] Remove duplicate logic from MCP server
- [ ] Add new MCP tools for categories/compose

### Phase 5: Favorites & Learning
- [ ] Favorites storage using MLflow runs (each generation = one run)
- [ ] Store `recipe_hash` and `category_hash` for drift detection
- [ ] Recipe extraction from favorites with transferable elements
- [ ] Cross-category recipe transfer
- [ ] Pattern learning (common successful combinations)
- [ ] Add `/api/v1/favorites` endpoints
- [ ] Implement favorite replay with category YAML drift warnings

### Phase 6: Web UI Layer
- [ ] Adopt model-manager's FastAPI + HTML/CSS/JS GUI architecture
- [ ] Chat interface with category awareness and @tag suggestions
- [ ] Visual preset builder (drag-drop category composition)
- [ ] Gallery integration with favorites and MLflow metadata
- [ ] Real-time preview of composed settings
- [ ] Category selector with visual icons

### Phase 7: Advanced NL Understanding
- [ ] LLM-powered intent parsing (optional)
- [ ] Context-aware suggestions based on category combinations
- [ ] Conversational refinement ("make it more dramatic")
- [ ] History-aware recipe suggestions

## Example Category Definition

```yaml
# categories/definitions/subjects/car.yaml
category:
  id: "car"
  type: "subject"
  display_name: "Vehicles & Automotive"
  description: "Cars, trucks, motorcycles - automotive photography"
  icon: "🚗"  # For UI
  
  # Keywords for NL matching
  keywords:
    primary: ["car", "vehicle", "automobile", "auto"]
    secondary: ["drive", "driving", "road", "highway", "street"]
    specific: ["ferrari", "porsche", "bmw", "tesla", "sports car", "sedan", "suv"]
  
  # Prompt engineering for this category
  prompts:
    positive_fragments:
      required:
        - "professional automotive photography"
      optional:
        - "(single car:1.4), isolated subject"  # Prevent duplicates
        - "studio lighting with reflections"
        - "clean lines, sharp details"
      
    negative_fragments:
      required:
        - "multiple vehicles, duplicate cars, two cars, three cars"
        - "car show, parking lot, traffic, convoy"
      optional:
        - "blurry wheels, distorted reflections"
    
    # Templates for this category
    templates:
      basic: "{color} {car_type}, {location}, {time_of_day}"
      detailed: "{color} {car_type} {action}, {location}, {time_of_day}, {lighting}, {camera}"
      
    variables:
      color: ["metallic silver", "deep blue", "guards red", "pristine white", "matte black"]
      car_type: ["sports car", "luxury sedan", "vintage convertible", "modern SUV"]
      action: ["parked", "in motion", "captured mid-corner", "positioned"]
      location: ["coastal highway", "modern showroom", "rain-soaked street", "mountain pass"]
  
  # Recommended LoRAs
  loras:
    required: []
    recommended:
      - filename: "more_details.safetensors"
        strength: 0.5
        reason: "Enhances fine mechanical details"
    
    avoid:
      - category: "anime"
        reason: "Conflicting style"
  
  # Generation settings
  settings:
    # Optimal settings for automotive
    cfg: 7.5
    steps: 50
    sampler: dpmpp_2m_sde
    scheduler: karras
    
    # Size recommendations
    sizes:
      landscape: { width: 1344, height: 768 }
      portrait: { width: 768, height: 1344 }
      square: { width: 1024, height: 1024 }
    
    default_size: "landscape"
  
  # Workflow preferences
  workflows:
    preferred: ["flux-dev.json", "realistic-vision.json"]
    compatible: ["pony-realism.json"]
    incompatible: ["wan22-t2v.json"]  # Video workflow
  
  # Composition rules
  composition:
    # Categories that enhance this one
    enhances_with:
      - "city"        # Cars in urban settings
      - "landscape"   # Cars in scenic locations
      - "night"       # Night photography
      - "rainy"       # Wet reflections
      
    # Categories that conflict
    conflicts_with:
      - "underwater"
      - "space"
      - "anime"  # Style conflict with photorealistic car
      
    # When combined with person
    with_person:
      role: "secondary"  # Car becomes prop, person is subject
      prompt_modifier: "standing next to, posing with"
    
    # Priority for setting merges
    priority: 0.8  # Subject categories have high priority
```

## CLI Integration

```bash
# Natural language mode
comfy-gen chat "sports car on rainy Tokyo street at night"

# Explicit tag mode
comfy-gen generate "@car @city @night red ferrari, wet streets, neon reflections"

# Use favorite settings
comfy-gen generate --favorite fav_001 "forest landscape at sunset"

# List categories
comfy-gen categories list
comfy-gen categories show car

# Compose preview (dry run)
comfy-gen compose "@car @city @night" --preview

# Builder mode
comfy-gen builder  # Opens TUI
```

## MCP Server Extensions

New tools for intelligent generation:

```python
@mcp.tool()
def intelligent_generate(
    prompt: str,
    categories: list[str] | None = None,
    use_favorite: str | None = None,
    preview_only: bool = False
) -> dict:
    """
    Generate image with intelligent category composition.
    
    Args:
        prompt: Natural language or @tag prompt
        categories: Explicit category overrides
        use_favorite: Apply settings from a favorite
        preview_only: Return composed recipe without generating
    """

@mcp.tool()
def list_categories(category_type: str | None = None) -> list:
    """List available categories, optionally filtered by type."""

@mcp.tool()
def compose_recipe(categories: list[str], subject: str) -> dict:
    """Preview how categories would compose into a recipe."""

@mcp.tool()
def mark_favorite(image_url: str, name: str, notes: str) -> str:
    """Mark an image as favorite and extract its recipe."""

@mcp.tool()
def apply_favorite(favorite_id: str, new_subject: str) -> dict:
    """Apply a favorite's settings to a new subject."""
```

## Success Metrics

1. **Category coverage**: 20+ categories across subjects, settings, modifiers, styles
2. **Composition quality**: Merged presets produce coherent prompts
3. **NL accuracy**: 80%+ of natural language requests correctly parsed
4. **Favorite reuse**: Users can successfully apply favorites cross-category
5. **Generation quality**: Intelligent presets match or exceed manual tuning

## Research & Best Practices

### Multi-LoRA Composition (Critical)

Based on research from "Multi-LoRA Composition for Image Generation" (Zhong et al., 2024):

**Problem:** Naive LoRA merging (simple weight addition) destabilizes as LoRA count increases, causing image distortion, deformed subjects, and detail loss.

**Solutions (Training-Free):**

| Method | How It Works | Best For | ComfyUI Support |
|--------|--------------|----------|-----------------|
| **LoRA Switch** | Alternate between LoRAs every τ steps (recommended τ=5) | Realistic images, composition quality | Custom node needed |
| **LoRA Composite** | Calculate CFG scores from each LoRA, average them | Anime style, image quality | Custom node needed |
| **LoRA Merge (Baseline)** | Linear weight combination W' = W + Σ(wi × BiAi) | 2-3 LoRAs max | Native ComfyUI |

**Key Findings:**
- **Activation order matters**: Start with character/subject LoRA, then clothing → style → background → object
- **Step size τ=5 is optimal** for LoRA Switch (switching every step causes distortion)
- **Performance degrades** significantly beyond 3-4 LoRAs with naive merging
- **LCM/Turbo compatibility**: Methods work with 4-8 step accelerated generation

**Implementation Strategy for ComfyGen:**
1. **For 2-3 LoRAs**: Use native ComfyUI LoRA stacking (already works)
2. **For 4+ LoRAs**: Implement LoRA Switch via custom workflow or warn user
3. **Always**: Enforce character/subject LoRA first in activation sequence
4. **Track**: Log LoRA combinations and quality scores to MLflow for pattern learning

### LoRA Stacking Policy (Product Rules)

A firm, enforceable policy for production use:

```yaml
# comfy_gen/config/lora_policy.yaml
lora_policy:
  # Hard caps by model family
  caps:
    sdxl: 4      # Max LoRAs for SDXL-based workflows
    flux: 3      # Flux is more sensitive to LoRA stacking
    sd15: 5      # SD 1.5 handles more LoRAs
    wan_video: 2 # Video workflows are very sensitive
  
  # Enforced ordering (categories from lora_catalog.yaml)
  ordering:
    1: ["character", "identity", "face"]      # Subject/identity first
    2: ["clothing", "outfit", "props"]        # What they're wearing/holding
    3: ["style", "aesthetic", "rendering"]    # How it looks
    4: ["environment", "background", "scene"] # Where they are
    5: ["detail", "quality", "enhancement"]   # Fine-tuning
  
  # Strategy selection
  strategies:
    default: "native"           # ComfyUI native stacking
    high_count: "lora_switch"   # When count > cap - 1
    fallback: "warn_and_cap"    # If custom workflow unavailable
  
  # User-facing selector in GUI
  user_selectable:
    - native     # Standard stacking
    - switch     # LoRA Switch (τ=5)
    - composite  # LoRA Composite (CFG averaging)
```

**Enforcement Logic:**
```python
def enforce_lora_policy(loras: list[LoRA], model_family: str) -> PolicyResult:
    cap = POLICY.caps[model_family]
    
    if len(loras) > cap:
        if POLICY.strategies["high_count"] == "lora_switch":
            return PolicyResult(
                loras=loras[:cap],  # Still cap for safety
                workflow_variant="lora-switch-variant.json",
                warning=f"Using LoRA Switch for {len(loras)} LoRAs"
            )
        else:
            return PolicyResult(
                loras=loras[:cap],
                warning=f"Capped at {cap} LoRAs for {model_family}. Dropped: {loras[cap:]}"
            )
    
    # Reorder by category priority
    ordered = sort_by_category_priority(loras)
    return PolicyResult(loras=ordered)
```

### Prompt Engineering Best Practices

From Shopify's Stable Diffusion guide and empirical testing:

**Prompt Structure (Order Matters!):**
```
[Subject] [Action/Pose], [Setting/Location], [Time/Weather], [Style], [Technical]
```
Keywords near the front get more weight in diffusion models.

**Critical Rules:**
1. **Avoid contradictions**: "sunny night", "rainy clear sky" degrade output
2. **Union negatives carefully**: Merge negative prompts, but watch for conflicts
3. **Be specific**: "red Ferrari 488 GTB" > "sports car"
4. **Weight syntax**: Use `(keyword:1.3)` for emphasis, but don't over-weight

**Single Subject Enforcement (Already in prompt_catalog.yaml):**
```yaml
positive_prefix: "(single woman:1.5), (one person only:1.4), isolated subject, solo,"
negative_additions: ["multiple people", "duplicate", "clone", "extra person"]
```

### Conflict Detection

Categories should detect and warn about conflicts:

| Conflict Type | Example | Resolution |
|---------------|---------|------------|
| **Semantic** | "rainy" + "sunny" | Warn user, pick one |
| **Style** | "anime" + "photorealistic" | Block combination |
| **Subject** | Two primary subjects | Designate primary/secondary |
| **LoRA** | Incompatible base models | Filter based on `compatible_with` |

**Implementation:**
```python
def check_conflicts(categories: list[Category]) -> list[Conflict]:
    conflicts = []
    
    # Check YAML-defined conflicts
    for cat in categories:
        for other in categories:
            if other.id in cat.conflicts_with:
                conflicts.append(Conflict(cat, other, "explicit"))
    
    # Check semantic conflicts (NLP or keyword rules)
    for cat1, cat2 in itertools.combinations(categories, 2):
        if keywords_conflict(cat1.keywords, cat2.keywords):
            conflicts.append(Conflict(cat1, cat2, "semantic"))
    
    return conflicts
```

### Favorites & Recipe Transfer

**What to Extract from Favorites:**
- Full prompt (positive and negative)
- LoRA stack with strengths
- Generation settings (steps, CFG, sampler, scheduler)
- Workflow used
- Seed (optional, for exact reproduction)

**Transfer Rules:**
1. **Preserve**: Style, lighting, camera settings, modifiers
2. **Replace**: Subject-specific prompt fragments, subject LoRAs
3. **Recalculate**: Settings that depend on subject category

**MLflow Integration:**
```python
# When marking favorite
log_favorite(
    image_url=url,
    recipe={
        "prompt": full_prompt,
        "negative_prompt": negative,
        "loras": lora_stack,
        "settings": generation_settings,
        "categories": detected_categories,
    },
    transferable_elements={
        "lighting": "golden hour with rim lighting",
        "composition": "rule of thirds",
        "style": "cinematic photography",
    }
)
```

### MLflow Provenance & Drift Detection

Treat each generation as an MLflow run with comprehensive provenance:

```python
import hashlib
import mlflow

def log_generation_run(recipe: Recipe, categories: list[str], image_url: str):
    \"\"\"Log generation with full provenance for reproducibility.\"\"\"
    
    # Compute deterministic hashes for drift detection
    recipe_hash = hashlib.sha256(
        json.dumps(recipe.dict(), sort_keys=True).encode()
    ).hexdigest()[:16]
    
    category_hash = hashlib.sha256(
        json.dumps(sorted(categories)).encode()
    ).hexdigest()[:16]
    
    with mlflow.start_run():
        # Core recipe as params (searchable)
        mlflow.log_params({
            "checkpoint": recipe.checkpoint,
            "workflow": recipe.workflow,
            "steps": recipe.steps,
            "cfg": recipe.cfg,
            "sampler": recipe.sampler,
            "scheduler": recipe.scheduler,
            "width": recipe.width,
            "height": recipe.height,
        })
        
        # LoRAs as individual params for filtering
        for i, lora in enumerate(recipe.loras):
            mlflow.log_param(f"lora_{i}_file", lora.filename)
            mlflow.log_param(f"lora_{i}_strength", lora.strength)
        
        # Hashes for drift detection
        mlflow.log_param("recipe_hash", recipe_hash)
        mlflow.log_param("category_hash", category_hash)
        mlflow.log_param("category_yaml_version", get_category_schema_version())
        
        # Categories as tags for filtering
        for cat in categories:
            mlflow.set_tag(f"category_{cat}", "true")
        
        # Full recipe as artifact (for exact replay)
        mlflow.log_dict(recipe.dict(), "recipe.json")
        
        # Image as artifact
        mlflow.set_tag("image_url", image_url)

def detect_favorite_drift(favorite_id: str) -> DriftReport:
    \"\"\"Check if category YAML has changed since favorite was saved.\"\"\"
    favorite_run = mlflow.get_run(favorite_id)
    
    saved_category_hash = favorite_run.data.params.get("category_hash")
    saved_yaml_version = favorite_run.data.params.get("category_yaml_version")
    
    current_categories = favorite_run.data.params.get("categories", "").split(",")
    current_hash = compute_category_hash(current_categories)
    
    if saved_category_hash != current_hash:
        return DriftReport(
            drifted=True,
            message=f"Category definitions changed since favorite was saved (v{saved_yaml_version} → v{get_category_schema_version()})",
            recommendation="Recipe may produce different results. Consider re-testing."
        )
    
    return DriftReport(drifted=False)
```

**Why this matters:** When category YAML evolves and a favorite replays, the merge logic may produce different prompts/settings. Hashes detect this drift proactively.

### Content Policy Layer

First-class content policy that runs between parsing and execution:

```python
# comfy_gen/services/policy/content_policy.py
from enum import Enum

class PolicyTier(Enum):
    GENERAL = "general"      # Safe for all audiences
    MATURE = "mature"        # Artistic nudity, violence
    EXPLICIT = "explicit"    # NSFW content

class ContentPolicy:
    \"\"\"Centralized content policy enforcement.\"\"\"
    
    def __init__(self, config: PolicyConfig):
        self.tier = config.tier
        self.allowed_categories = config.allowed_categories
        self.blocked_categories = config.blocked_categories
        self.model_allowlist = config.model_allowlist
    
    def check(self, request: GenerationRequest) -> PolicyResult:
        \"\"\"Run policy checks between parsing and execution.\"\"\"
        
        # 1. Category-level gating
        for cat in request.categories:
            if cat.id in self.blocked_categories:
                return PolicyResult(
                    allowed=False,
                    reason=f"Category '{cat.id}' blocked by policy"
                )
            
            if cat.requires_tier and cat.requires_tier.value > self.tier.value:
                return PolicyResult(
                    allowed=False,
                    reason=f"Category '{cat.id}' requires {cat.requires_tier.value} tier"
                )
        
        # 2. Model/workflow allowlist
        if self.model_allowlist:
            if request.checkpoint not in self.model_allowlist:
                return PolicyResult(
                    allowed=False,
                    reason=f"Checkpoint '{request.checkpoint}' not in allowlist"
                )
        
        # 3. Automatic fragment redaction (for edge cases)
        redacted_prompt = self.redact_incompatible_fragments(
            request.prompt, 
            request.categories
        )
        
        return PolicyResult(
            allowed=True,
            redacted_prompt=redacted_prompt if redacted_prompt != request.prompt else None
        )
```

**Configuration per user/deployment:**
```yaml
# comfy_gen/config/policy.yaml
policy:
  default_tier: "explicit"  # For personal deployment
  
  category_rules:
    nsfw:
      requires_tier: "explicit"
      allowed_models: ["pornmasterProPony*", "majicmixRealistic*"]
    
    violence:
      requires_tier: "mature"
      blocked_fragments: ["gore", "dismemberment"]
  
  # For multi-user deployments
  user_overrides:
    guest:
      tier: "general"
      blocked_categories: ["nsfw", "violence"]
```

**Integration point:** Policy runs in the API layer, BEFORE hitting the service layer. UI layers don't need to know about policy - it's transparent.

### Category Schema Versioning

YAML velocity creates drift risk. Mitigate with schema validation and versioning:

```yaml
# categories/schema_version.yaml
schema:
  version: "1.2.0"
  
  # Semver rules:
  # MAJOR: Breaking changes (field removed, type changed)
  # MINOR: New optional fields, new categories
  # PATCH: Documentation, bug fixes
  
  migrations:
    "1.0.0_to_1.1.0":
      - action: "rename_field"
        from: "prompt_fragments"
        to: "prompts.positive_fragments"
    
    "1.1.0_to_1.2.0":
      - action: "add_field"
        field: "policy_tier"
        default: "general"
```

**Validation at load time:**
```python
from jsonschema import validate, ValidationError

def load_category(yaml_path: Path) -> Category:
    \"\"\"Load category with strict schema validation.\"\"\"
    
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    
    # Validate against JSON schema
    try:
        validate(data, CATEGORY_SCHEMA)
    except ValidationError as e:
        raise CategoryLoadError(
            f"Invalid category YAML at {yaml_path}: {e.message}\n"
            f"Path: {'/'.join(str(p) for p in e.absolute_path)}"
        )
    
    # Check schema version compatibility
    if data.get("schema_version", "1.0.0") < MINIMUM_SCHEMA_VERSION:
        raise CategoryLoadError(
            f"Category at {yaml_path} uses schema v{data.get('schema_version')} "
            f"but minimum is v{MINIMUM_SCHEMA_VERSION}. Run migration."
        )
    
    return Category(**data)
```

**Benefits:**
- **Fail-fast** with friendly errors (not cryptic KeyError at runtime)
- **Migration hooks** for evolving schemas without breaking existing categories
- **Drift detection** when favorites replay with newer category definitions

### Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| No category matched | Fall back to "general" category or prompt for clarification |
| Unknown @tag | Return error with suggestions from similar tags |
| Empty workflow intersection | Prefer image over video, warn user |
| Too many LoRAs (>4) | Warn about quality degradation, suggest alternatives |
| Conflicting settings | Use primary subject's settings, log warning |

### Testing Strategy

**Automated Tests:**
1. **Parser accuracy**: Suite of NL prompts → expected categories
2. **Composition correctness**: Category combinations → valid recipes
3. **Conflict detection**: Known conflicts trigger warnings
4. **Round-trip**: Generate → favorite → transfer → generate

**Quality Metrics (via MLflow):**
- Track user ratings per category combination
- A/B test LoRA stacking strategies
- Mine successful patterns for default recommendations

## Dependencies

- **Existing infrastructure**: MLflow (cerebro), MinIO (moira), ComfyUI (moira)
- **New dependencies**: 
  - `pyyaml` (already have)
  - `rich` for TUI builder (optional)
  - Optionally: local LLM for NL parsing (via model-manager)

## Existing Foundation (What We Already Have)

The comfy-gen codebase already has significant infrastructure that aligns with this architecture:

### Already Implemented ✅

| Component | File | Status |
|-----------|------|--------|
| **LoRA Catalog** | `lora_catalog.yaml` | Rich metadata: tags, compatible_with, recommended_strength, use_cases |
| **Prompt Catalog** | `prompt_catalog.yaml` | Categories, quality boosters, negative presets, templates, single-subject patterns |
| **LLM Enhancement** | `generate.py` | `--enhance-prompt`, `--enhance-style` flags for LLM-powered prompt improvement |
| **Quality Validation** | `generate.py` | `--quality-threshold`, `--max-attempts`, `--retry-strategy` for iterative refinement |
| **MLflow Logging** | `comfy_gen/mlflow_logger.py` | Comprehensive experiment tracking with category/ethnicity/scene tags |
| **MCP Server** | `mcp_server.py` | Existing tools for generation, can be extended |
| **Gallery Server** | cerebro | Image browsing and metadata display |

---

## Implementation Status (2026-01-07)

This section maps the architectural design to actual implemented code.

### Implemented Modules

| Component | Module Path | Key Classes/Functions |
|-----------|-------------|----------------------|
| **Category Schema** | `comfy_gen/categories/schema.json` | JSON Schema v1.0.0 |
| **Category Registry** | `comfy_gen/categories/registry.py` | `CategoryRegistry` (singleton) |
| **Category Validator** | `comfy_gen/categories/validator.py` | `validate_category()`, `validate_all_categories()` |
| **Tag Parser** | `comfy_gen/parsing/tag_parser.py` | `TagParser`, `TagMatch`, `ParseResult` |
| **Intent Classifier** | `comfy_gen/parsing/intent_classifier.py` | `IntentClassifier`, `HybridParser`, `CategoryMatch` |
| **Composition Engine** | `comfy_gen/composition/engine.py` | `CompositionEngine`, `CompositionResult` |
| **Recipe Builder** | `comfy_gen/composition/recipe.py` | `RecipeBuilder`, `Recipe` |
| **Content Policy** | `comfy_gen/policy/content_policy.py` | `PolicyEnforcer`, `PolicyLevel`, `check_policy()` |
| **Workflow Manifest** | `comfy_gen/workflows/manifest.py` | `WorkflowManifest`, `ResolutionConstraint` |
| **Workflow Registry** | `comfy_gen/workflows/registry.py` | `WorkflowRegistry` (singleton) |
| **MLflow Tracker** | `comfy_gen/tracking/mlflow_tracker.py` | `MLflowTracker`, `ProvenanceHashes`, `GenerationResult` |
| **FastAPI App** | `comfy_gen/api/app.py` | `app`, `create_app()` |
| **Web GUI** | `comfy_gen/gui/routes.py` | `setup_gui()`, Jinja2 templates |

### API Endpoints

| Endpoint | Route Module | Status |
|----------|--------------|--------|
| `POST /compose` | `comfy_gen/api/routes/compose.py` | ✅ Implemented |
| `POST /compose/preview` | `comfy_gen/api/routes/compose.py` | ✅ Implemented |
| `GET /categories` | `comfy_gen/api/routes/categories.py` | ✅ Implemented |
| `GET /categories/{id}` | `comfy_gen/api/routes/categories.py` | ✅ Implemented |
| `POST /favorites` | `comfy_gen/api/routes/favorites.py` | ✅ Implemented |
| `GET /favorites` | `comfy_gen/api/routes/favorites.py` | ✅ Implemented |
| `DELETE /favorites/{id}` | `comfy_gen/api/routes/favorites.py` | ✅ Implemented |
| `POST /favorites/{id}/extract-recipe` | `comfy_gen/api/routes/favorites.py` | ✅ Implemented |
| `PUT /favorites/{id}/rating` | `comfy_gen/api/routes/favorites.py` | ✅ Implemented |
| `POST /generate` | `comfy_gen/api/routes/generation.py` | ✅ Implemented |
| `GET /generate/{id}` | `comfy_gen/api/routes/generation.py` | ✅ Implemented |
| `GET /health` | `comfy_gen/api/app.py` | ✅ Implemented |

### Pydantic Schemas

| Schema | Module | Purpose |
|--------|--------|---------|
| `Category` | `comfy_gen/api/schemas/category.py` | Category response model |
| `Recipe` | `comfy_gen/api/schemas/recipe.py` | Generation recipe model |
| `ExplanationBlock` | `comfy_gen/api/schemas/explanation.py` | Composition explanation |
| `ComposeRequest/Response` | `comfy_gen/api/schemas/compose.py` | Compose endpoint models |
| `GenerationRequest/Response` | `comfy_gen/api/schemas/generation.py` | Generate endpoint models |

### GUI Components

| Template | Path | Purpose |
|----------|------|---------|
| `base.html` | `comfy_gen/gui/templates/base.html` | Base layout with navigation |
| `index.html` | `comfy_gen/gui/templates/index.html` | Generation interface |
| `compose.html` | `comfy_gen/gui/templates/compose.html` | Intelligent composition |
| `categories.html` | `comfy_gen/gui/templates/categories.html` | Category browser |
| `gallery.html` | `comfy_gen/gui/templates/gallery.html` | Favorites gallery |

| JavaScript | Path | Purpose |
|------------|------|---------|
| `api.js` | `comfy_gen/gui/static/js/api.js` | `ComfyGenAPI` client class |
| `generate.js` | `comfy_gen/gui/static/js/generate.js` | Generation page logic |
| `compose.js` | `comfy_gen/gui/static/js/compose.js` | Composition page logic |
| `categories.js` | `comfy_gen/gui/static/js/categories.js` | Category browser logic |
| `gallery.js` | `comfy_gen/gui/static/js/gallery.js` | Favorites gallery logic |

### Phase Status Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | FastAPI skeleton + services | ✅ Complete |
| 1 | Category System (YAML, schema, registry) | ✅ Complete |
| 2 | Parser + Compose Endpoint + Policy | ✅ Complete |
| 3 | CLI Migration to API | ⏳ Planned |
| 4 | MCP Migration to API | ⏳ Planned |
| 5 | MLflow + Favorites | ✅ Complete |
| 6 | Web GUI | ✅ Complete |

### Configuration Files

| File | Purpose |
|------|---------|
| `comfy_gen/categories/schema.json` | JSON Schema for category validation |
| `comfy_gen/categories/schema_version.yaml` | Schema versioning info |
| `comfy_gen/categories/definitions/` | Category YAML files |

---

## Related Files

- [presets.yaml](../presets.yaml) - Existing generation presets
- [lora_catalog.yaml](../lora_catalog.yaml) - LoRA metadata
- [prompt_catalog.yaml](../prompt_catalog.yaml) - Prompt templates
- [USAGE.md](./USAGE.md) - Current CLI usage
- [API_REFERENCE.md](./API_REFERENCE.md) - API endpoint documentation
- [CATEGORY_AUTHORING.md](./CATEGORY_AUTHORING.md) - How to create categories

## Architectural North Star

> **The system produces two outputs every time: a deterministic, replayable recipe AND an explanation tree that justifies it.**

This pair transforms comfy-gen from a generator into a **trusted system**:

1. **Recipe** = What happened (reproducible)
2. **Explanation** = Why it happened (debuggable)

When something looks wrong, users don't have to guess. The explanation shows:
- Which categories matched (and what keywords triggered them)
- How conflicts were resolved
- Why each LoRA was selected
- What drove the workflow choice

This transparency builds trust and enables rapid iteration. The recipe is the contract; the explanation is the audit trail.
