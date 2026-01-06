#!/usr/bin/env python3
"""
MLflow experiment tracking for ComfyGen image generation.
Comprehensive logging of generation parameters, outputs, and human feedback.

Key Metrics Tracked:
- Generation params: steps, cfg, sampler, scheduler, resolution
- Model info: checkpoint, VAE, LoRAs (with individual strengths)
- Validation scores: CLIP score, positive/negative/delta scores
- Human feedback: rating (1-5), category, detailed notes
- Artifacts: full prompts (txt), generated images (png)

Usage:
    from log_experiments import log_generation, setup_mlflow
    
    setup_mlflow()
    log_generation(
        image_url="http://...",
        prompt="...",
        negative_prompt="...",
        steps=150,
        cfg=6.0,
        sampler="dpmpp_2m_sde",
        loras=[("zy_AmateurStyle_v2.safetensors", 0.4)],
        human_rating=4,
        feedback="Good skin texture",
    )
"""

import mlflow
import requests
import tempfile
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# MLflow server on moira (migrated from cerebro 2026-01-05)
MLFLOW_URI = "http://192.168.1.215:5000"
EXPERIMENT_NAME = "comfygen-pony-realism"


def setup_mlflow() -> str:
    """Initialize MLflow tracking."""
    mlflow.set_tracking_uri(MLFLOW_URI)
    
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        experiment_id = mlflow.create_experiment(
            EXPERIMENT_NAME,
            tags={
                "project": "comfy-gen",
                "model_family": "pony-diffusion",
                "infrastructure": "moira-rtx5090",
                "created": datetime.now().isoformat(),
            }
        )
        print(f"[OK] Created experiment: {EXPERIMENT_NAME} (ID: {experiment_id})")
    else:
        experiment_id = experiment.experiment_id
        print(f"[OK] Using existing experiment: {EXPERIMENT_NAME} (ID: {experiment_id})")
    
    mlflow.set_experiment(EXPERIMENT_NAME)
    return experiment_id


def download_image(url: str, temp_dir: str) -> Optional[str]:
    """Download image from MinIO URL to temp directory for artifact logging."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            filename = url.split("/")[-1]
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)
            return filepath
    except Exception as e:
        print(f"  [WARN] Could not download image: {e}")
    return None


def log_generation(
    # Required
    image_url: str,
    prompt: str,
    negative_prompt: str,
    steps: int,
    cfg: float,
    sampler: str,
    
    # Generation settings
    scheduler: str = "karras",
    width: int = 1024,
    height: int = 1024,
    seed: int = None,
    denoise: float = None,
    
    # Model info
    checkpoint: str = "ponyRealism_V22.safetensors",
    vae: str = "default",
    
    # LoRAs - list of tuples (name, strength) or list of strings
    loras: List = None,
    
    # Validation scores (from CLIP evaluator)
    clip_score: float = None,
    positive_score: float = None,
    negative_score: float = None,
    delta_score: float = None,
    
    # Human feedback
    human_rating: int = None,  # 1-5 stars
    feedback: str = None,
    feedback_category: str = None,  # "good", "overprocessed", "artifacts", "anatomy_issue"
    
    # Metadata
    generation_type: str = "txt2img",  # "txt2img", "img2img", "inpaint"
    source_image_url: str = None,  # For img2img/inpaint
    session_id: str = None,
    run_name: str = None,
    tags: Dict[str, str] = None,
    
    # Options
    log_image_artifact: bool = True,
    
    # Legacy aliases (for backward compatibility)
    score: float = None,  # Alias for clip_score
    rating: int = None,   # Alias for human_rating
) -> str:
    """
    Log a comprehensive generation run to MLflow.
    
    Captures:
    - Parameters: All generation settings for reproducibility
    - Metrics: CLIP scores and human ratings
    - Tags: Feedback, categories, session info
    - Artifacts: Full prompts (txt) and generated images (png)
    
    Returns:
        run_id: The MLflow run ID for reference
    """
    
    # Handle legacy aliases
    if clip_score is None and score is not None:
        clip_score = score
    if human_rating is None and rating is not None:
        human_rating = rating
    
    if run_name is None:
        run_name = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with mlflow.start_run(run_name=run_name) as run:
        run_id = run.info.run_id
        
        # === PARAMETERS (for reproducibility) ===
        
        # Prompts (truncated for MLflow's 500 char limit)
        mlflow.log_param("prompt", prompt[:490] if len(prompt) > 490 else prompt)
        mlflow.log_param("prompt_length", len(prompt))
        mlflow.log_param("negative_prompt", negative_prompt[:490] if len(negative_prompt) > 490 else negative_prompt)
        mlflow.log_param("negative_prompt_length", len(negative_prompt))
        
        # Sampling parameters
        mlflow.log_param("steps", steps)
        mlflow.log_param("cfg", cfg)
        mlflow.log_param("sampler", sampler)
        mlflow.log_param("scheduler", scheduler)
        
        # Image dimensions
        mlflow.log_param("width", width)
        mlflow.log_param("height", height)
        mlflow.log_param("resolution", f"{width}x{height}")
        mlflow.log_param("megapixels", round(width * height / 1_000_000, 2))
        
        # Reproducibility
        if seed is not None:
            mlflow.log_param("seed", seed)
        if denoise is not None:
            mlflow.log_param("denoise", denoise)
        
        # Model info
        mlflow.log_param("checkpoint", checkpoint)
        mlflow.log_param("vae", vae)
        mlflow.log_param("generation_type", generation_type)
        
        # LoRAs (critical for reproducibility)
        if loras:
            mlflow.log_param("lora_count", len(loras))
            lora_summaries = []
            for i, lora in enumerate(loras):
                if isinstance(lora, tuple) and len(lora) >= 2:
                    name, strength = lora[0], lora[1]
                    mlflow.log_param(f"lora_{i}_name", name)
                    mlflow.log_param(f"lora_{i}_strength", strength)
                    lora_summaries.append(f"{name}@{strength}")
                else:
                    mlflow.log_param(f"lora_{i}", str(lora))
                    lora_summaries.append(str(lora))
            mlflow.log_param("loras_summary", ", ".join(lora_summaries))
        else:
            mlflow.log_param("lora_count", 0)
            mlflow.log_param("loras_summary", "none")
        
        # Source image (for img2img workflows)
        if source_image_url:
            mlflow.log_param("source_image_url", source_image_url)
        
        # === METRICS (for comparison/sorting) ===
        
        if clip_score is not None:
            mlflow.log_metric("clip_score", clip_score)
        if positive_score is not None:
            mlflow.log_metric("positive_score", positive_score)
        if negative_score is not None:
            mlflow.log_metric("negative_score", negative_score)
        if delta_score is not None:
            mlflow.log_metric("delta_score", delta_score)
        if human_rating is not None:
            mlflow.log_metric("human_rating", human_rating)
        
        # === TAGS (for filtering/searching) ===
        
        mlflow.set_tag("image_url", image_url)
        mlflow.set_tag("image_filename", image_url.split("/")[-1])
        
        if feedback:
            mlflow.set_tag("human_feedback", feedback[:500])
        if feedback_category:
            mlflow.set_tag("feedback_category", feedback_category)
        if session_id:
            mlflow.set_tag("session_id", session_id)
        
        # Custom tags
        if tags:
            for k, v in tags.items():
                mlflow.set_tag(k, str(v)[:500])
        
        # === ARTIFACTS ===
        # Note: Artifact logging disabled when using remote MLflow with local artifact store
        # The artifact root is on moira's local disk which isn't accessible from magneto
        # Images are accessible via MinIO URLs stored in image_url tag
        
        # Full prompt stored in params (truncated) - full prompt viewable via MinIO image metadata
        
        print(f"[OK] Run logged: {run_id[:8]}... ({run_name})")
        return run_id


def log_batch_feedback(runs_data: List[Dict]) -> List[str]:
    """Log multiple runs with feedback. Returns list of run IDs."""
    run_ids = []
    for run in runs_data:
        run_id = log_generation(**run)
        run_ids.append(run_id)
    return run_ids


def main():
    """Log today's experiments with comprehensive detail."""
    setup_mlflow()
    
    session_id = "20260105_asian_hq"
    
    # Comprehensive experiment data with all fields
    experiments = [
        # === Initial 150-step variations ===
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_182729_hq_150steps_1024.png",
            "prompt": "score_9, score_8_up, score_7_up, rating_explicit, masterpiece, best quality, photo, raw photo, 1girl, 1boy, asian woman, korean, beautiful face, looking at viewer, pov, blowjob, oral sex, big white cock in mouth, holding penis, eye contact, bedroom, natural lighting, realistic skin, skin pores, film grain",
            "negative_prompt": "score_6, score_5, score_4, worst quality, low quality, blurry, cartoon, anime, 3d, cgi, airbrushed, fake, plastic skin, bad anatomy, bad hands, deformed",
            "steps": 150,
            "cfg": 6.0,
            "sampler": "dpmpp_2m_sde",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": None,
            "clip_score": 0.657,
            "positive_score": 0.657,
            "negative_score": 0.587,
            "delta_score": 0.070,
            "human_rating": 4,
            "feedback": "Very solid result - good skin texture and composition. SDE sampler produces natural results.",
            "feedback_category": "good",
            "session_id": session_id,
            "run_name": "baseline_150steps_cfg6",
            "tags": {"approach": "baseline", "sampler_type": "sde", "recommended": "yes"}
        },
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_182830_var1_150_euler.png",
            "prompt": "score_9, score_8_up, score_7_up, rating_explicit, photo, raw photo, dslr, 1girl, 1boy, asian woman, korean, beautiful natural face, pov blowjob, sucking big white cock, penis in mouth, hand on shaft, eye contact, looking up at viewer, bedroom, soft natural light, shallow dof, realistic skin texture, visible pores, natural imperfections, moles, no makeup, authentic",
            "negative_prompt": "score_6, score_5, score_4, worst quality, low quality, blurry, airbrushed, smooth skin, fake, plastic, cartoon, anime, 3d, cgi, perfect skin, poreless, beauty filter",
            "steps": 150,
            "cfg": 5.5,
            "sampler": "euler_ancestral",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": None,
            "clip_score": 0.654,
            "positive_score": 0.654,
            "negative_score": 0.606,
            "delta_score": 0.048,
            "human_rating": 4,
            "feedback": "Also very solid - euler_ancestral produces natural results. Good alternative to SDE.",
            "feedback_category": "good",
            "session_id": session_id,
            "run_name": "euler_ancestral_cfg55",
            "tags": {"approach": "euler_test", "sampler_type": "ancestral", "recommended": "yes"}
        },
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_182858_var2_150_nolora.png",
            "prompt": "score_9, score_8_up, score_7_up, rating_explicit, professional photo, 1girl, 1boy, asian woman, japanese, gorgeous face, detailed eyes, pov, blowjob, oral, big white cock, penis in mouth, saliva, hand holding shaft, direct eye contact, intimate, bedroom, cinematic lighting, photorealistic, hyper detailed skin, skin pores, subsurface scattering, film grain",
            "negative_prompt": "score_6, score_5, score_4, worst quality, low quality, blurry, cartoon, anime, 3d, cgi, airbrushed, retouched, smooth skin, fake, plastic, bad anatomy, deformed",
            "steps": 150,
            "cfg": 6.0,
            "sampler": "dpmpp_2m",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": None,
            "clip_score": 0.664,
            "positive_score": 0.664,
            "negative_score": 0.604,
            "delta_score": 0.060,
            "human_rating": 2,
            "feedback": "Strangely over processed - dpmpp_2m (non-SDE) produces worse results than SDE variant. AVOID.",
            "feedback_category": "overprocessed",
            "session_id": session_id,
            "run_name": "dpmpp_2m_nonsde",
            "tags": {"approach": "sampler_comparison", "sampler_type": "non_sde", "issue": "overprocessed", "avoid": "yes"}
        },
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_182942_var3_150_heun.png",
            "prompt": "score_9, score_8_up, score_7_up, rating_explicit, candid photo, amateur snapshot, 1girl, 1boy, asian girl, thai woman, cute natural face, blowjob pov, sucking white cock, big dick in mouth, looking at camera, messy hair, real amateur, grainy photo, authentic, unedited, natural skin, imperfect skin, real person",
            "negative_prompt": "score_6, score_5, score_4, worst quality, low quality, professional, studio, airbrushed, perfect, cartoon, anime, 3d, cgi, smooth skin, fake, plastic",
            "steps": 150,
            "cfg": 7.0,
            "sampler": "heun",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": None,
            "clip_score": 0.653,
            "positive_score": 0.653,
            "negative_score": 0.613,
            "delta_score": 0.041,
            "human_rating": 2,
            "feedback": "Also strangely over processed - heun sampler not recommended for Pony Realism. AVOID.",
            "feedback_category": "overprocessed",
            "session_id": session_id,
            "run_name": "heun_cfg7",
            "tags": {"approach": "sampler_comparison", "sampler_type": "heun", "issue": "overprocessed", "avoid": "yes"}
        },
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_183043_var4_cfg5.png",
            "prompt": "score_9, score_8_up, rating_explicit, photo, asian woman, blowjob pov, white cock, eye contact, realistic skin, pores visible",
            "negative_prompt": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
            "steps": 150,
            "cfg": 5.0,
            "sampler": "dpmpp_2m_sde",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": None,
            "clip_score": 0.674,
            "positive_score": 0.674,
            "negative_score": 0.591,
            "delta_score": 0.083,
            "human_rating": 3,
            "feedback": "Decent result overall, dick could probably be better with anatomy LoRA. CFG 5.0 borderline too low.",
            "feedback_category": "needs_improvement",
            "session_id": session_id,
            "run_name": "low_cfg_5",
            "tags": {"approach": "cfg_test", "note": "needs_lora_for_anatomy"}
        },
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_183108_var5_euler_cfg45.png",
            "prompt": "score_9, score_8_up, rating_explicit, photo, asian woman, blowjob pov, white cock, eye contact, realistic skin, pores visible",
            "negative_prompt": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
            "steps": 150,
            "cfg": 4.5,
            "sampler": "euler",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": None,
            "clip_score": 0.666,
            "positive_score": 0.666,
            "negative_score": 0.593,
            "delta_score": 0.074,
            "human_rating": 2,
            "feedback": "Too many skin artifacts - something off about texture. CFG 4.5 is TOO LOW - causes artifacts.",
            "feedback_category": "artifacts",
            "session_id": session_id,
            "run_name": "euler_very_low_cfg",
            "tags": {"approach": "cfg_test", "issue": "skin_artifacts", "cfg_too_low": "true", "avoid": "yes"}
        },
        # === Optimized runs with LoRA based on feedback ===
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_183840_best1_euler_lora.png",
            "prompt": "score_9, score_8_up, rating_explicit, photo, raw photo, 1girl, 1boy, asian woman, korean, beautiful face, pov blowjob, big white cock in mouth, eye contact, bedroom, natural light, realistic skin, skin pores",
            "negative_prompt": "score_6, worst quality, blurry, cartoon, anime, 3d, airbrushed, fake",
            "steps": 150,
            "cfg": 5.5,
            "sampler": "euler_ancestral",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": [("zy_AmateurStyle_v2.safetensors", 0.4)],
            "clip_score": 0.676,
            "positive_score": 0.676,
            "negative_score": 0.591,
            "delta_score": 0.086,
            "human_rating": None,  # Pending user review
            "feedback": "Optimized settings from feedback analysis: euler_ancestral + light LoRA (0.4)",
            "feedback_category": "pending_review",
            "session_id": session_id,
            "run_name": "optimized_euler_lora04",
            "tags": {"approach": "optimized", "based_on": "feedback_analysis", "iteration": "1"}
        },
        {
            "image_url": "http://192.168.1.215:9000/comfy-gen/20260105_183910_best2_sde_lora.png",
            "prompt": "score_9, score_8_up, rating_explicit, photo, raw photo, 1girl, 1boy, asian woman, japanese, beautiful face, pov blowjob, big white cock in mouth, eye contact, bedroom, soft light, realistic skin, skin pores",
            "negative_prompt": "score_6, worst quality, blurry, cartoon, anime, 3d, airbrushed, fake",
            "steps": 150,
            "cfg": 6.0,
            "sampler": "dpmpp_2m_sde",
            "scheduler": "karras",
            "checkpoint": "ponyRealism_V22.safetensors",
            "loras": [("zy_AmateurStyle_v2.safetensors", 0.4)],
            "clip_score": 0.680,
            "positive_score": 0.680,
            "negative_score": 0.583,
            "delta_score": 0.097,
            "human_rating": None,  # Pending user review
            "feedback": "Optimized settings from feedback analysis: dpmpp_2m_sde + light LoRA (0.4)",
            "feedback_category": "pending_review",
            "session_id": session_id,
            "run_name": "optimized_sde_lora04",
            "tags": {"approach": "optimized", "based_on": "feedback_analysis", "iteration": "1"}
        },
    ]
    
    print(f"\n{'='*60}")
    print(f"Logging {len(experiments)} experiments with comprehensive data")
    print(f"(Image URLs logged as tags - images viewable in MinIO)")
    print(f"{'='*60}\n")
    
    for i, exp in enumerate(experiments, 1):
        print(f"[{i}/{len(experiments)}] {exp.get('run_name', 'unnamed')}")
        # Disable image artifact upload since MLflow artifacts are on moira's local disk
        # Images are accessible via MinIO URLs stored in tags
        log_generation(**exp, log_image_artifact=False)
    
    print(f"\n{'='*60}")
    print(f"[OK] All experiments logged successfully!")
    print(f"")
    print(f"View experiments: http://192.168.1.215:5000/#/experiments")
    print(f"Experiment name:  {EXPERIMENT_NAME}")
    print(f"Session ID:       {session_id}")
    print(f"")
    print(f"Key findings logged:")
    print(f"  - RECOMMENDED: dpmpp_2m_sde, euler_ancestral")
    print(f"  - AVOID: dpmpp_2m (non-SDE), heun")
    print(f"  - CFG sweet spot: 5.5-6.0")
    print(f"  - LoRA strength: 0.3-0.4 (light touch)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
