#!/usr/bin/env python3
"""
MASSIVE EXPERIMENT FRAMEWORK
============================
4-5 hour comprehensive run generating 250+ images with full variance.

Goals:
- Every scenario type (settings, acts, compositions)
- Every ethnicity/body type combination
- Every technical parameter variation
- Full metadata capture for reproducibility
- MLflow logging with complete experiment details

Estimated runtime: 250 images × ~90 seconds = ~6 hours
"""

import hashlib
import json
import random
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import mlflow

# ============================================================================
# CONFIGURATION
# ============================================================================

MLFLOW_URI = "http://192.168.1.215:5000"
EXPERIMENT_NAME = "comfy-gen-massive-experiment"
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"
OUTPUT_DIR = Path("/tmp/massive_experiment")
METADATA_DIR = OUTPUT_DIR / "metadata"

# Quality prefix/suffix for Pony Realism
QUALITY_PREFIX = "score_9, score_8_up, score_7_up, source_photo, raw photo, photorealistic, hyperrealistic, ultra detailed, masterpiece"
QUALITY_SUFFIX = "8k uhd, high resolution, professional photography, sharp focus, intricate details"

# Enhanced negative prompt
BASE_NEGATIVE = """score_6, score_5, score_4, blurry, low quality, jpeg artifacts, pixelated, grainy,
bad anatomy, deformed, disfigured, mutation, extra limbs, missing limbs,
watermark, signature, text, logo, cartoon, anime, illustration, drawing, painting, 3d render, cgi,
trans, transgender, futanari, futa, hermaphrodite, shemale, dickgirl"""

# ============================================================================
# VARIANCE DEFINITIONS
# ============================================================================

# --- ETHNICITIES & BODY TYPES ---
ETHNICITIES = [
    {"name": "japanese", "skin": "porcelain skin", "hair": "dark silky hair", "features": "delicate asian features"},
    {"name": "korean", "skin": "flawless pale skin", "hair": "black straight hair", "features": "elegant korean features"},
    {"name": "chinese", "skin": "smooth fair skin", "hair": "dark hair", "features": "refined chinese features"},
    {"name": "vietnamese", "skin": "warm tan skin", "hair": "dark wavy hair", "features": "soft vietnamese features"},
    {"name": "thai", "skin": "golden tan skin", "hair": "dark hair", "features": "exotic thai features"},
    {"name": "filipino", "skin": "warm brown skin", "hair": "dark hair", "features": "mixed filipino features"},
    {"name": "indian", "skin": "rich brown skin", "hair": "dark thick hair", "features": "striking indian features"},
    {"name": "middle_eastern", "skin": "olive skin", "hair": "dark hair", "features": "exotic middle eastern features"},
    {"name": "latina", "skin": "caramel skin", "hair": "dark wavy hair", "features": "passionate latina features"},
    {"name": "brazilian", "skin": "golden tan skin", "hair": "dark curly hair", "features": "exotic brazilian features"},
    {"name": "african", "skin": "rich ebony skin", "hair": "dark natural hair", "features": "striking african features"},
    {"name": "african_american", "skin": "brown skin", "hair": "dark hair", "features": "beautiful black features"},
    {"name": "caucasian_brunette", "skin": "fair skin", "hair": "brown hair", "features": "classic european features"},
    {"name": "caucasian_blonde", "skin": "pale skin", "hair": "blonde hair", "features": "nordic features"},
    {"name": "caucasian_redhead", "skin": "pale freckled skin", "hair": "red hair", "features": "irish features"},
    {"name": "russian", "skin": "pale porcelain skin", "hair": "light brown hair", "features": "slavic features"},
    {"name": "mediterranean", "skin": "olive tan skin", "hair": "dark hair", "features": "mediterranean features"},
    {"name": "mixed_asian_white", "skin": "light tan skin", "hair": "dark hair", "features": "mixed eurasian features"},
    {"name": "mixed_black_white", "skin": "caramel skin", "hair": "curly hair", "features": "mixed race features"},
]

BODY_TYPES = [
    {"name": "petite", "desc": "petite slim body, small frame", "breasts": "small perky breasts"},
    {"name": "slim", "desc": "slim toned body", "breasts": "small natural breasts"},
    {"name": "athletic", "desc": "athletic toned body, fit", "breasts": "firm medium breasts"},
    {"name": "average", "desc": "average body type", "breasts": "medium natural breasts"},
    {"name": "curvy", "desc": "curvy hourglass figure", "breasts": "large natural breasts"},
    {"name": "voluptuous", "desc": "voluptuous full figured", "breasts": "very large breasts"},
    {"name": "busty_slim", "desc": "slim body with large chest", "breasts": "large breasts on slim frame"},
]

AGES = [
    {"name": "young", "desc": "young woman in her early 20s"},
    {"name": "mid_twenties", "desc": "woman in her mid 20s"},
    {"name": "late_twenties", "desc": "woman in her late 20s"},
    {"name": "early_thirties", "desc": "woman in her early 30s"},
    {"name": "milf", "desc": "attractive mature woman in her 30s-40s"},
]

# --- SETTINGS/LOCATIONS ---
SETTINGS = [
    {"name": "bedroom_luxury", "desc": "luxury bedroom with silk sheets, warm ambient lighting, elegant decor"},
    {"name": "bedroom_simple", "desc": "simple bedroom, natural lighting from window, clean sheets"},
    {"name": "hotel_room", "desc": "upscale hotel room, mood lighting, city view through window"},
    {"name": "bathroom_shower", "desc": "steamy bathroom, wet skin, water droplets, shower tiles"},
    {"name": "bathroom_tub", "desc": "luxurious bathtub, bubbles, candles, soft lighting"},
    {"name": "living_room", "desc": "modern living room, leather couch, ambient lighting"},
    {"name": "kitchen", "desc": "modern kitchen, marble countertop, morning light"},
    {"name": "office", "desc": "private office, desk, professional setting"},
    {"name": "car_interior", "desc": "car interior, leather seats, confined space"},
    {"name": "car_backseat", "desc": "car backseat, cramped space, steamy windows"},
    {"name": "pool_outdoor", "desc": "outdoor pool area, sunny day, poolside lounger"},
    {"name": "beach", "desc": "private beach, sunset, sand, ocean in background"},
    {"name": "forest_outdoor", "desc": "secluded forest clearing, dappled sunlight, nature"},
    {"name": "balcony", "desc": "private balcony, city skyline, night lights"},
    {"name": "studio_photo", "desc": "professional photo studio, softbox lighting, clean background"},
    {"name": "gym", "desc": "private gym, workout equipment, mirrors"},
    {"name": "sauna", "desc": "wooden sauna, steam, warm lighting"},
    {"name": "jacuzzi", "desc": "private jacuzzi, bubbling water, mood lighting"},
]

# --- SCENARIO CATEGORIES ---
SOLO_FEMALE_SCENARIOS = [
    {"name": "nude_portrait", "prompt": "nude portrait, {subject}, standing pose, full body, {setting}", "category": "solo_female"},
    {"name": "nude_lying", "prompt": "nude woman lying on back, {subject}, relaxed pose, legs visible, {setting}", "category": "solo_female"},
    {"name": "nude_sitting", "prompt": "nude woman sitting, {subject}, legs crossed or spread, {setting}", "category": "solo_female"},
    {"name": "lingerie_tease", "prompt": "woman in sexy lingerie, {subject}, teasing pose, {setting}", "category": "solo_female"},
    {"name": "masturbating", "prompt": "woman masturbating, {subject}, fingers on pussy, pleasured expression, {setting}", "category": "solo_female"},
    {"name": "spread_pussy", "prompt": "woman spreading pussy lips, {subject}, explicit view, lying back, {setting}", "category": "solo_female"},
    {"name": "ass_pose", "prompt": "woman showing ass, {subject}, bent over pose, looking back, {setting}", "category": "solo_female"},
    {"name": "breast_grab", "prompt": "woman grabbing her own breasts, {subject}, squeezing, sensual expression, {setting}", "category": "solo_female"},
    {"name": "wet_shower", "prompt": "woman in shower, {subject}, wet skin, water running down body, {setting}", "category": "solo_female"},
]

SOLO_MALE_SCENARIOS = [
    {"name": "male_nude", "prompt": "nude muscular man, athletic body, erect penis visible, {setting}", "category": "solo_male"},
    {"name": "male_stroking", "prompt": "man stroking his erect penis, muscular body, self pleasure, {setting}", "category": "solo_male"},
]

COUPLE_ORAL_SCENARIOS = [
    {"name": "blowjob_pov", "prompt": "pov blowjob, {subject}, mouth around cock, looking up at camera, {setting}", "category": "oral"},
    {"name": "blowjob_side", "prompt": "side angle blowjob, {subject}, profile view, mouth on shaft, {setting}", "category": "oral"},
    {"name": "blowjob_above", "prompt": "blowjob from above angle, {subject}, kneeling woman, looking up, {setting}", "category": "oral"},
    {"name": "deepthroat", "prompt": "deepthroat, {subject}, full insertion, throat bulge, watery eyes, {setting}", "category": "oral"},
    {"name": "licking_cock", "prompt": "licking cock, {subject}, tongue on shaft, teasing, {setting}", "category": "oral"},
    {"name": "licking_balls", "prompt": "licking balls, {subject}, tongue on testicles, submissive pose, {setting}", "category": "oral"},
    {"name": "two_hand_blowjob", "prompt": "two handed blowjob, {subject}, both hands on shaft, mouth on tip, {setting}", "category": "oral"},
    {"name": "sloppy_blowjob", "prompt": "sloppy blowjob, {subject}, saliva dripping, messy, enthusiastic, {setting}", "category": "oral"},
    {"name": "facefuck", "prompt": "facefuck, {subject}, man holding her head, rough oral, {setting}", "category": "oral"},
]

COUPLE_HANDJOB_SCENARIOS = [
    {"name": "handjob_front", "prompt": "handjob, {subject}, woman stroking penis, front view, {setting}", "category": "handjob"},
    {"name": "handjob_side", "prompt": "handjob side view, {subject}, profile of woman stroking cock, {setting}", "category": "handjob"},
    {"name": "two_hand_handjob", "prompt": "two handed handjob, {subject}, both hands gripping shaft, {setting}", "category": "handjob"},
    {"name": "handjob_sitting", "prompt": "handjob while sitting together, {subject}, intimate pose, {setting}", "category": "handjob"},
]

COUPLE_SEX_SCENARIOS = [
    {"name": "missionary", "prompt": "missionary sex, {subject}, man on top, penetration, intimate, {setting}", "category": "sex"},
    {"name": "missionary_pov", "prompt": "pov missionary, {subject}, woman on back, legs spread, penetration visible, {setting}", "category": "sex"},
    {"name": "doggy_style", "prompt": "doggy style sex, {subject}, woman on all fours, rear penetration, {setting}", "category": "sex"},
    {"name": "doggy_pov", "prompt": "pov doggy style, {subject}, ass up, penetration from behind, {setting}", "category": "sex"},
    {"name": "cowgirl", "prompt": "cowgirl position, {subject}, woman riding on top, facing camera, {setting}", "category": "sex"},
    {"name": "reverse_cowgirl", "prompt": "reverse cowgirl, {subject}, woman riding facing away, ass visible, {setting}", "category": "sex"},
    {"name": "spooning", "prompt": "spooning sex, {subject}, side lying penetration, intimate, {setting}", "category": "sex"},
    {"name": "standing_sex", "prompt": "standing sex against wall, {subject}, lifted leg, penetration, {setting}", "category": "sex"},
    {"name": "prone_bone", "prompt": "prone bone position, {subject}, woman flat on stomach, rear penetration, {setting}", "category": "sex"},
]

COUPLE_TITJOB_SCENARIOS = [
    {"name": "titjob", "prompt": "titjob, titty fucking, {subject}, cock between large breasts, {setting}", "category": "titjob"},
    {"name": "titjob_pov", "prompt": "pov titjob, {subject}, breasts wrapped around cock, looking up, {setting}", "category": "titjob"},
]

CUMSHOT_SCENARIOS = [
    {"name": "facial_cumshot", "prompt": "facial cumshot, cum on face, {subject}, cum dripping from face, {setting}", "category": "cumshot"},
    {"name": "cum_in_mouth", "prompt": "cum in mouth, {subject}, mouth open receiving cum, cum on tongue, {setting}", "category": "cumshot"},
    {"name": "cum_on_tits", "prompt": "cum on tits, {subject}, cum covered breasts, thick ropes of cum, {setting}", "category": "cumshot"},
    {"name": "cum_on_ass", "prompt": "cum on ass, {subject}, cum on butt cheeks, bent over, {setting}", "category": "cumshot"},
    {"name": "cum_on_back", "prompt": "cum on back, {subject}, lying on stomach, cum on lower back, {setting}", "category": "cumshot"},
    {"name": "cum_dripping", "prompt": "cum dripping from pussy, {subject}, creampie aftermath, cum leaking, {setting}", "category": "cumshot"},
    {"name": "bukkake", "prompt": "bukkake, excessive cum, {subject}, face covered in cum, multiple loads, {setting}", "category": "cumshot"},
    {"name": "cum_swallow", "prompt": "swallowing cum, {subject}, cum in mouth, swallowing, satisfied expression, {setting}", "category": "cumshot"},
]

THREESOME_SCENARIOS = [
    {"name": "mff_oral", "prompt": "threesome mff, two women giving blowjob together, sharing cock, {setting}", "category": "threesome"},
    {"name": "mff_sex", "prompt": "threesome mff, man fucking one woman while other watches, {setting}", "category": "threesome"},
    {"name": "mmf_dp", "prompt": "threesome mmf, double penetration, woman between two men, {setting}", "category": "threesome"},
    {"name": "mmf_spit_roast", "prompt": "spit roast, woman sucking one cock while fucked from behind, {setting}", "category": "threesome"},
]

LESBIAN_SCENARIOS = [
    {"name": "lesbian_kiss", "prompt": "two women kissing passionately, lesbian, intimate embrace, {setting}", "category": "lesbian"},
    {"name": "lesbian_oral", "prompt": "lesbian oral sex, woman going down on another woman, cunnilingus, {setting}", "category": "lesbian"},
    {"name": "lesbian_69", "prompt": "lesbian 69 position, two women pleasuring each other simultaneously, {setting}", "category": "lesbian"},
    {"name": "lesbian_tribbing", "prompt": "tribbing, scissoring, two women grinding pussies together, {setting}", "category": "lesbian"},
]

# Combine all scenarios
ALL_SCENARIOS = (
    SOLO_FEMALE_SCENARIOS +
    SOLO_MALE_SCENARIOS +
    COUPLE_ORAL_SCENARIOS +
    COUPLE_HANDJOB_SCENARIOS +
    COUPLE_SEX_SCENARIOS +
    COUPLE_TITJOB_SCENARIOS +
    CUMSHOT_SCENARIOS +
    THREESOME_SCENARIOS +
    LESBIAN_SCENARIOS
)

# --- TECHNICAL PARAMETERS ---
SAMPLERS = [
    "dpmpp_2m_sde",
    "dpmpp_2m",
    "euler_ancestral",
    "euler",
    "dpmpp_sde",
    "dpmpp_2s_ancestral",
    "uni_pc",
    "ddim",
]

SCHEDULERS = [
    "karras",
    "normal",
    "exponential",
    "sgm_uniform",
]

STEP_RANGES = [
    (30, "fast"),
    (50, "standard"),
    (80, "quality"),
    (120, "high_quality"),
    (150, "ultra_quality"),
]

CFG_RANGES = [
    (4.0, "low"),
    (5.5, "medium_low"),
    (6.5, "medium"),
    (7.5, "medium_high"),
    (8.5, "high"),
    (10.0, "very_high"),
]

# --- LORA COMBINATIONS ---
LORA_PRESETS = {
    "realism_basic": [
        ("zy_AmateurStyle_v2.safetensors", 0.4),
    ],
    "realism_enhanced": [
        ("zy_AmateurStyle_v2.safetensors", 0.35),
        ("add_detail.safetensors", 0.3),
    ],
    "skin_focus": [
        ("polyhedron_skin.safetensors", 0.4),
        ("realora_skin.safetensors", 0.3),
    ],
    "amateur_grainy": [
        ("zy_AmateurStyle_v2.safetensors", 0.5),
        ("more_details.safetensors", 0.2),
    ],
    "nsfw_action": [
        ("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5),
        ("zy_AmateurStyle_v2.safetensors", 0.3),
    ],
    "nsfw_detailed": [
        ("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5),
        ("add_detail.safetensors", 0.3),
    ],
    "cumshot_realistic": [
        ("realcumv6.55.safetensors", 0.7),
        ("zy_AmateurStyle_v2.safetensors", 0.3),
    ],
    "cumshot_heavy": [
        ("realcumv6.55.safetensors", 0.7),
        ("extreme_bukkake_pony.safetensors", 0.4),
    ],
    "high_detail": [
        ("add_detail.safetensors", 0.4),
        ("more_details.safetensors", 0.3),
    ],
    "skin_detail": [
        ("polyhedron_skin.safetensors", 0.35),
        ("add_detail.safetensors", 0.3),
    ],
}

# Map scenario categories to appropriate LoRA presets
CATEGORY_LORA_MAPPING = {
    "solo_female": ["realism_basic", "realism_enhanced", "skin_focus", "amateur_grainy", "high_detail"],
    "solo_male": ["realism_basic", "skin_focus"],
    "oral": ["nsfw_action", "nsfw_detailed", "realism_enhanced", "amateur_grainy"],
    "handjob": ["nsfw_action", "nsfw_detailed", "realism_enhanced"],
    "sex": ["nsfw_action", "nsfw_detailed", "realism_enhanced", "skin_focus"],
    "titjob": ["nsfw_action", "realism_enhanced", "skin_focus"],
    "cumshot": ["cumshot_realistic", "cumshot_heavy"],
    "threesome": ["nsfw_action", "nsfw_detailed"],
    "lesbian": ["realism_enhanced", "skin_focus", "high_detail"],
}

# ============================================================================
# DATA CLASSES FOR EXPERIMENT TRACKING
# ============================================================================

@dataclass
class ExperimentConfig:
    """Complete configuration for a single experiment."""
    experiment_id: str
    timestamp: str

    # Subject details
    ethnicity: str
    body_type: str
    age_range: str
    subject_prompt: str

    # Scenario details
    scenario_name: str
    scenario_category: str
    scenario_prompt_template: str

    # Setting
    setting_name: str
    setting_description: str

    # Technical parameters
    sampler: str
    scheduler: str
    steps: int
    steps_category: str
    cfg: float
    cfg_category: str

    # LoRA configuration
    lora_preset_name: str
    loras: List[Tuple[str, float]]

    # Final prompts
    full_positive_prompt: str
    full_negative_prompt: str

    # Output
    output_filename: str
    workflow_file: str = "workflows/pony-realism.json"

    def to_dict(self):
        return asdict(self)

    def generate_hash(self) -> str:
        """Generate unique hash for this configuration."""
        key_params = f"{self.scenario_name}_{self.ethnicity}_{self.sampler}_{self.steps}_{self.cfg}_{self.lora_preset_name}"
        return hashlib.md5(key_params.encode()).hexdigest()[:8]


@dataclass
class ExperimentResult:
    """Results from running an experiment."""
    config: ExperimentConfig
    success: bool
    minio_url: Optional[str]
    validation_score: Optional[float]
    validation_passed: bool
    generation_time_seconds: float
    error_message: Optional[str]


# ============================================================================
# EXPERIMENT GENERATION
# ============================================================================

def build_subject_prompt(ethnicity: dict, body_type: dict, age: dict) -> str:
    """Build a complete subject description."""
    return f"beautiful {age['desc']}, {ethnicity['name'].replace('_', ' ')} woman, {body_type['desc']}, {ethnicity['skin']}, {ethnicity['hair']}, {ethnicity['features']}, {body_type['breasts']}"


def build_full_prompt(scenario: dict, subject: str, setting: dict) -> str:
    """Build the complete positive prompt."""
    base_prompt = scenario["prompt"]
    base_prompt = base_prompt.replace("{subject}", subject)
    base_prompt = base_prompt.replace("{setting}", setting["desc"])

    return f"{QUALITY_PREFIX}, {base_prompt}, {QUALITY_SUFFIX}"


def generate_experiment_configs(count: int, seed: int = None) -> List[ExperimentConfig]:
    """Generate a diverse set of experiment configurations."""
    if seed:
        random.seed(seed)

    configs = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure we cover all scenario categories proportionally
    scenario_weights = {
        "solo_female": 0.15,
        "solo_male": 0.03,
        "oral": 0.20,
        "handjob": 0.10,
        "sex": 0.25,
        "titjob": 0.05,
        "cumshot": 0.12,
        "threesome": 0.05,
        "lesbian": 0.05,
    }

    # Generate target counts per category
    category_counts = {cat: int(count * weight) for cat, weight in scenario_weights.items()}

    # Fill remaining slots
    remaining = count - sum(category_counts.values())
    for _ in range(remaining):
        cat = random.choice(list(scenario_weights.keys()))
        category_counts[cat] += 1

    exp_num = 0
    for category, cat_count in category_counts.items():
        # Get scenarios for this category
        category_scenarios = [s for s in ALL_SCENARIOS if s.get("category") == category]
        if not category_scenarios:
            continue

        for _i in range(cat_count):
            scenario = random.choice(category_scenarios)
            ethnicity = random.choice(ETHNICITIES)
            body_type = random.choice(BODY_TYPES)
            age = random.choice(AGES)
            setting = random.choice(SETTINGS)

            # Technical parameters with some bias toward proven good values
            sampler = random.choice(SAMPLERS)
            scheduler = random.choice(SCHEDULERS)
            steps, steps_cat = random.choice(STEP_RANGES)
            cfg, cfg_cat = random.choice(CFG_RANGES)

            # LoRA preset based on category
            available_presets = CATEGORY_LORA_MAPPING.get(category, ["realism_basic"])
            lora_preset_name = random.choice(available_presets)
            loras = LORA_PRESETS[lora_preset_name]

            # Build prompts
            subject_prompt = build_subject_prompt(ethnicity, body_type, age)
            full_prompt = build_full_prompt(scenario, subject_prompt, setting)

            # Create config
            config = ExperimentConfig(
                experiment_id=f"exp_{exp_num:04d}",
                timestamp=timestamp,
                ethnicity=ethnicity["name"],
                body_type=body_type["name"],
                age_range=age["name"],
                subject_prompt=subject_prompt,
                scenario_name=scenario["name"],
                scenario_category=category,
                scenario_prompt_template=scenario["prompt"],
                setting_name=setting["name"],
                setting_description=setting["desc"],
                sampler=sampler,
                scheduler=scheduler,
                steps=steps,
                steps_category=steps_cat,
                cfg=cfg,
                cfg_category=cfg_cat,
                lora_preset_name=lora_preset_name,
                loras=loras,
                full_positive_prompt=full_prompt,
                full_negative_prompt=BASE_NEGATIVE,
                output_filename=f"{timestamp}_exp_{exp_num:04d}_{scenario['name']}_{ethnicity['name']}.png",
            )

            configs.append(config)
            exp_num += 1

    # Shuffle to mix categories
    random.shuffle(configs)

    return configs


# ============================================================================
# EXECUTION
# ============================================================================

def run_single_experiment(config: ExperimentConfig) -> ExperimentResult:
    """Run a single experiment and return results."""
    import re
    import time

    start_time = time.time()

    output_path = OUTPUT_DIR / config.output_filename

    cmd = [
        sys.executable, str(GENERATE_PY),
        "--workflow", config.workflow_file,
        "--prompt", config.full_positive_prompt,
        "--negative-prompt", config.full_negative_prompt,
        "--steps", str(config.steps),
        "--cfg", str(config.cfg),
        "--sampler", config.sampler,
        "--scheduler", config.scheduler,
        "--output", str(output_path),
    ]

    # Add LoRAs
    for lora_name, lora_strength in config.loras:
        cmd.extend(["--lora", f"{lora_name}:{lora_strength}"])

    try:
        result = subprocess.run(
            cmd,
            cwd=str(COMFY_GEN_DIR),
            capture_output=True,
            text=True,
            timeout=900,
        )

        elapsed = time.time() - start_time

        # Parse output
        output = result.stdout + result.stderr
        minio_url = None
        validation_score = None
        passed = False

        for line in output.split("\n"):
            if "http://192.168.1.215:9000/comfy-gen/" in line and ".png" in line and ".json" not in line:
                match = re.search(r'(http://192\.168\.1\.215:9000/comfy-gen/[^\s]+\.png)', line)
                if match:
                    minio_url = match.group(1)
            if "Score:" in line:
                try:
                    validation_score = float(line.split(":")[-1].strip())
                except:
                    pass
            if "Validation: PASSED" in line:
                passed = True

        return ExperimentResult(
            config=config,
            success=result.returncode == 0,
            minio_url=minio_url,
            validation_score=validation_score,
            validation_passed=passed,
            generation_time_seconds=elapsed,
            error_message=result.stderr[-300:] if result.returncode != 0 else None,
        )

    except subprocess.TimeoutExpired:
        return ExperimentResult(
            config=config,
            success=False,
            minio_url=None,
            validation_score=None,
            validation_passed=False,
            generation_time_seconds=900,
            error_message="Timeout after 900 seconds",
        )
    except Exception as e:
        return ExperimentResult(
            config=config,
            success=False,
            minio_url=None,
            validation_score=None,
            validation_passed=False,
            generation_time_seconds=time.time() - start_time,
            error_message=str(e),
        )


def save_experiment_metadata(config: ExperimentConfig, result: ExperimentResult):
    """Save complete metadata for an experiment."""
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    metadata = {
        "config": config.to_dict(),
        "result": {
            "success": result.success,
            "minio_url": result.minio_url,
            "validation_score": result.validation_score,
            "validation_passed": result.validation_passed,
            "generation_time_seconds": result.generation_time_seconds,
            "error_message": result.error_message,
        }
    }

    metadata_path = METADATA_DIR / f"{config.experiment_id}.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def log_to_mlflow(config: ExperimentConfig, result: ExperimentResult):
    """Log experiment to MLflow with full details."""
    with mlflow.start_run(run_name=f"{config.experiment_id}_{config.scenario_name}"):
        # Log all config parameters
        mlflow.log_param("experiment_id", config.experiment_id)
        mlflow.log_param("scenario_name", config.scenario_name)
        mlflow.log_param("scenario_category", config.scenario_category)
        mlflow.log_param("ethnicity", config.ethnicity)
        mlflow.log_param("body_type", config.body_type)
        mlflow.log_param("age_range", config.age_range)
        mlflow.log_param("setting", config.setting_name)
        mlflow.log_param("sampler", config.sampler)
        mlflow.log_param("scheduler", config.scheduler)
        mlflow.log_param("steps", config.steps)
        mlflow.log_param("steps_category", config.steps_category)
        mlflow.log_param("cfg", config.cfg)
        mlflow.log_param("cfg_category", config.cfg_category)
        mlflow.log_param("lora_preset", config.lora_preset_name)
        mlflow.log_param("loras", str([l[0] for l in config.loras]))
        mlflow.log_param("workflow", config.workflow_file)

        # Log prompts (truncated for MLflow limits)
        mlflow.log_param("prompt_preview", config.full_positive_prompt[:500])

        # Log results as metrics
        mlflow.log_metric("success", 1 if result.success else 0)
        mlflow.log_metric("generation_time", result.generation_time_seconds)
        if result.validation_score is not None:
            mlflow.log_metric("validation_score", result.validation_score)
        mlflow.log_metric("validation_passed", 1 if result.validation_passed else 0)

        # Log URL and metadata as tags
        if result.minio_url:
            mlflow.set_tag("minio_url", result.minio_url)
        mlflow.set_tag("config_hash", config.generate_hash())
        mlflow.set_tag("subject_prompt", config.subject_prompt[:200])


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Massive experiment framework")
    parser.add_argument("--count", type=int, default=250, help="Number of experiments")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--dry-run", action="store_true", help="Preview without running")
    parser.add_argument("--start-from", type=int, default=0, help="Start from experiment N")
    args = parser.parse_args()

    print("=" * 70)
    print("MASSIVE EXPERIMENT FRAMEWORK")
    print("=" * 70)

    # Generate experiment configs
    print(f"\n[INFO] Generating {args.count} experiment configurations...")
    configs = generate_experiment_configs(args.count, seed=args.seed)

    # Print statistics
    categories = {}
    ethnicities = {}
    settings = {}
    lora_presets = {}

    for c in configs:
        categories[c.scenario_category] = categories.get(c.scenario_category, 0) + 1
        ethnicities[c.ethnicity] = ethnicities.get(c.ethnicity, 0) + 1
        settings[c.setting_name] = settings.get(c.setting_name, 0) + 1
        lora_presets[c.lora_preset_name] = lora_presets.get(c.lora_preset_name, 0) + 1

    print("\n[STATS] Category distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} ({100*count/len(configs):.1f}%)")

    print("\n[STATS] Top ethnicities:")
    for eth, count in sorted(ethnicities.items(), key=lambda x: -x[1])[:10]:
        print(f"  {eth}: {count}")

    print("\n[STATS] LoRA presets:")
    for preset, count in sorted(lora_presets.items(), key=lambda x: -x[1]):
        print(f"  {preset}: {count}")

    estimated_time = len(configs) * 90 / 3600  # ~90 seconds per image
    print(f"\n[INFO] Estimated runtime: {estimated_time:.1f} hours")

    if args.dry_run:
        print("\n[DRY RUN] Sample experiments:")
        for i, c in enumerate(configs[:20]):
            loras = "+".join([l[0].split(".")[0][:10] for l in c.loras])
            print(f"  {i+1}. {c.scenario_name} | {c.ethnicity} | {c.setting_name} | {c.sampler} s={c.steps} | {loras}")
        return

    # Setup
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Run experiments
    results = []
    start_idx = args.start_from

    print(f"\n[INFO] Starting from experiment {start_idx}")
    print(f"[INFO] Output directory: {OUTPUT_DIR}")
    print(f"[INFO] Metadata directory: {METADATA_DIR}")
    print("-" * 70)

    for i, config in enumerate(configs[start_idx:], start=start_idx):
        print(f"\n[{i+1}/{len(configs)}] {config.experiment_id}: {config.scenario_name}")
        print(f"  Subject: {config.ethnicity} {config.body_type} {config.age_range}")
        print(f"  Setting: {config.setting_name}")
        print(f"  Tech: {config.sampler} s={config.steps} cfg={config.cfg} sched={config.scheduler}")
        lora_str = "+".join([f"{l[0].split('.')[0][:12]}@{l[1]}" for l in config.loras])
        print(f"  LoRAs: {lora_str}")

        result = run_single_experiment(config)
        results.append(result)

        # Save metadata immediately
        save_experiment_metadata(config, result)

        # Log to MLflow
        try:
            log_to_mlflow(config, result)
        except Exception as e:
            print(f"  [WARN] MLflow logging failed: {e}")

        # Print result
        status = "[OK]" if result.success else "[FAIL]"
        time_str = f"{result.generation_time_seconds:.1f}s"
        score_str = f"score={result.validation_score:.3f}" if result.validation_score else ""
        print(f"  {status} {time_str} {score_str}")
        if result.minio_url:
            print(f"  URL: {result.minio_url}")
        if result.error_message:
            print(f"  Error: {result.error_message[:100]}")

        # Progress update every 25 images
        if (i + 1) % 25 == 0:
            success_count = sum(1 for r in results if r.success)
            avg_time = sum(r.generation_time_seconds for r in results) / len(results)
            remaining = len(configs) - i - 1
            eta_hours = (remaining * avg_time) / 3600
            print(f"\n  >>> Progress: {i+1}/{len(configs)} | Success: {success_count}/{len(results)} | ETA: {eta_hours:.1f}h <<<\n")

    # Final summary
    print("\n" + "=" * 70)
    print("MASSIVE EXPERIMENT COMPLETE")
    print("=" * 70)

    total = len(results)
    successes = sum(1 for r in results if r.success)
    scores = [r.validation_score for r in results if r.validation_score]
    total_time = sum(r.generation_time_seconds for r in results)

    print(f"\nTotal experiments: {total}")
    print(f"Successful: {successes} ({100*successes/total:.1f}%)")
    print(f"Failed: {total - successes}")
    print(f"Total time: {total_time/3600:.2f} hours")
    print(f"Average time per image: {total_time/total:.1f} seconds")

    if scores:
        print("\nValidation scores:")
        print(f"  Average: {sum(scores)/len(scores):.3f}")
        print(f"  Best: {max(scores):.3f}")
        print(f"  Worst: {min(scores):.3f}")

    # Category breakdown
    print("\nSuccess by category:")
    for cat in sorted(set(c.scenario_category for c in configs)):
        cat_results = [r for r in results if r.config.scenario_category == cat]
        cat_success = sum(1 for r in cat_results if r.success)
        print(f"  {cat}: {cat_success}/{len(cat_results)} ({100*cat_success/len(cat_results):.0f}%)")

    print(f"\nMetadata saved to: {METADATA_DIR}")
    print(f"MLflow experiment: {EXPERIMENT_NAME}")
    print(f"MLflow UI: {MLFLOW_URI}")


if __name__ == "__main__":
    main()
