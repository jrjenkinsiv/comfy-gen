"""
MLflow experiment logging for ComfyGen.

Comprehensive schema captures ALL generation parameters.
"""
import mlflow
from typing import Optional, Dict, Any, List
import json
import os

MLFLOW_URI = "http://192.168.1.162:5001"
DEFAULT_EXPERIMENT = "comfy-gen-nsfw"

# ALL parameters we want to capture - be exhaustive
GENERATION_PARAMS = {
    # Model params (REQUIRED)
    "checkpoint": "Base model checkpoint file",
    "workflow": "Workflow JSON file used",
    
    # Sampling params (REQUIRED)
    "steps": "Number of sampling steps",
    "cfg": "CFG scale (classifier-free guidance)",
    "sampler": "Sampler algorithm (euler, euler_ancestral, dpm_2, etc)",
    "scheduler": "Scheduler type (normal, karras, exponential, etc)",
    "seed": "Random seed (-1 for random)",
    
    # Image params (REQUIRED)
    "width": "Output width in pixels",
    "height": "Output height in pixels",
    
    # LoRA params (capture ALL)
    "loras": "Comma-separated LoRAs with strengths: name:strength,name:strength",
    "lora_count": "Number of LoRAs used",
    
    # Prompt params (capture FULL text)
    "prompt": "Full positive prompt",
    "negative_prompt": "Full negative prompt",
    "prompt_length": "Token count of positive prompt",
    
    # Subject params
    "ethnicity": "Subject ethnicity/race",
    "hair_color": "Hair color",
    "body_type": "Body type description",
    "cup_size": "Breast size if applicable",
    "expression": "Facial expression",
    "age_range": "Approximate age range (20s, 30s, etc)",
    
    # Scene params
    "scene": "Scene type (handjob_pov, blowjob, etc)",
    "setting": "Location/environment",
    "lighting": "Lighting conditions",
    "camera_angle": "Camera angle/perspective",
    
    # Technical params
    "vae": "VAE model used",
    "clip_skip": "CLIP skip value",
    "denoise": "Denoise strength for img2img",
    
    # Session metadata
    "session": "Session date/identifier",
    "batch_id": "Batch generation ID if applicable",
}

# These are the absolute minimum required
REQUIRED_PARAMS = ["checkpoint", "workflow", "steps", "cfg", "width", "height", "sampler"]


def check_mlflow_health() -> bool:
    """Check if MLflow is reachable."""
    import requests
    try:
        resp = requests.get(f"{MLFLOW_URI}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def parse_loras(lora_string: str) -> Dict[str, float]:
    """Parse lora string into dict. Format: 'name:0.4,name2:0.3'"""
    if not lora_string:
        return {}
    result = {}
    for item in lora_string.split(","):
        if ":" in item:
            name, strength = item.strip().split(":")
            result[name.strip()] = float(strength)
    return result


def log_experiment(
    run_name: str,
    image_url: str,
    params: dict,
    validation_score: float,
    user_rating: int,
    feedback: str,
    favorite: bool = False,
    experiment_name: str = DEFAULT_EXPERIMENT,
    prompt: str = None,
    negative_prompt: str = None,
) -> Optional[str]:
    """
    Log an experiment to MLflow with comprehensive schema.
    
    Args:
        run_name: Name for this run
        image_url: MinIO URL of generated image
        params: Dict of ALL generation parameters
        validation_score: Automated validation score (0-1)
        user_rating: User rating (1-5)
        feedback: User feedback text
        favorite: Mark as favorite
        experiment_name: MLflow experiment name
        prompt: Full positive prompt (also accepted in params)
        negative_prompt: Full negative prompt (also accepted in params)
        
    Returns:
        Run ID if successful, None if failed
    """
    # Handle prompt passed as arg or in params
    if prompt:
        params["prompt"] = prompt
    if negative_prompt:
        params["negative_prompt"] = negative_prompt
    
    # Auto-calculate derived params
    if "prompt" in params:
        params["prompt_length"] = len(params["prompt"].split())
    if "loras" in params:
        lora_dict = parse_loras(params["loras"])
        params["lora_count"] = len(lora_dict)
        # Also log individual LoRA strengths
        for lora_name, strength in lora_dict.items():
            params[f"lora_{lora_name}"] = strength
    
    # Check required params
    missing = [p for p in REQUIRED_PARAMS if p not in params]
    if missing:
        print(f"[WARN] Missing REQUIRED params: {missing}")
        print("       These are essential for experiment reproducibility!")
    
    # Check recommended params
    recommended = ["loras", "prompt", "negative_prompt", "seed", "scheduler"]
    missing_rec = [p for p in recommended if p not in params]
    if missing_rec:
        print(f"[INFO] Missing recommended params: {missing_rec}")
    
    # Check MLflow health
    if not check_mlflow_health():
        print(f"[ERROR] MLflow not reachable at {MLFLOW_URI}")
        print("        Try: ssh cerebro 'printf \"babyseal\\n\" | sudo -S pmset -a displaysleep 0 sleep 0 disksleep 0 powernap 0'")
        return None
    
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        mlflow.set_experiment(experiment_name)
        
        # Enable system metrics logging
        with mlflow.start_run(run_name=run_name) as run:
            # Log ALL params
            mlflow.log_params(params)
            
            # Log metrics
            mlflow.log_metric("validation_score", validation_score)
            mlflow.log_metric("user_rating", user_rating)
            
            # Log tags (for searchability)
            mlflow.set_tag("user_feedback", feedback)
            mlflow.set_tag("image_url", image_url)
            mlflow.set_tag("minio_bucket", "comfy-gen")
            
            if favorite:
                mlflow.set_tag("favorite", "true")
            
            # Extract filename for artifact reference
            if image_url:
                filename = image_url.split("/")[-1]
                mlflow.set_tag("image_filename", filename)
            
            # Log checkpoint and workflow as tags too for easy filtering
            if "checkpoint" in params:
                mlflow.set_tag("checkpoint", params["checkpoint"])
            if "ethnicity" in params:
                mlflow.set_tag("ethnicity", params["ethnicity"])
            if "scene" in params:
                mlflow.set_tag("scene", params["scene"])
            
            run_id = run.info.run_id
            print(f"[OK] Logged {run_name} to MLflow (run_id: {run_id[:8]}...)")
            print(f"     Params: {len(params)} | Rating: {user_rating}/5")
            return run_id
            
    except Exception as e:
        print(f"[ERROR] Failed to log to MLflow: {e}")
        return None


def log_favorite(
    run_name: str,
    image_url: str,
    params: dict,
    feedback: str = "FAVORITE",
    prompt: str = None,
    negative_prompt: str = None,
) -> Optional[str]:
    """Shorthand for logging a favorite with 5/5 rating."""
    return log_experiment(
        run_name=run_name,
        image_url=image_url,
        params=params,
        validation_score=1.0,
        user_rating=5,
        feedback=feedback,
        favorite=True,
        experiment_name="comfy-gen-nsfw-favorites",
        prompt=prompt,
        negative_prompt=negative_prompt,
    )


def log_batch(experiments: List[Dict[str, Any]], experiment_name: str = DEFAULT_EXPERIMENT) -> List[str]:
    """Log multiple experiments in batch."""
    run_ids = []
    for exp in experiments:
        run_id = log_experiment(
            run_name=exp["run_name"],
            image_url=exp["image_url"],
            params=exp["params"],
            validation_score=exp.get("validation_score", 0.0),
            user_rating=exp.get("user_rating", 0),
            feedback=exp.get("feedback", ""),
            favorite=exp.get("favorite", False),
            experiment_name=experiment_name,
            prompt=exp.get("prompt"),
            negative_prompt=exp.get("negative_prompt"),
        )
        if run_id:
            run_ids.append(run_id)
    return run_ids


def get_standard_params(
    checkpoint: str,
    workflow: str,
    steps: int,
    cfg: float,
    width: int,
    height: int,
    sampler: str = "euler_ancestral",
    scheduler: str = "normal",
    seed: int = -1,
    loras: str = "",
    prompt: str = "",
    negative_prompt: str = "",
    **kwargs
) -> dict:
    """Helper to build a complete params dict with all standard fields."""
    params = {
        "checkpoint": checkpoint,
        "workflow": workflow,
        "steps": steps,
        "cfg": cfg,
        "width": width,
        "height": height,
        "sampler": sampler,
        "scheduler": scheduler,
        "seed": seed,
        "loras": loras,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
    }
    params.update(kwargs)
    return params


# Print schema when run directly
if __name__ == "__main__":
    print("=" * 60)
    print("MLflow Logger for ComfyGen - Parameter Schema")
    print("=" * 60)
    print(f"\nMLflow URI: {MLFLOW_URI}")
    print(f"Health: {'[OK]' if check_mlflow_health() else '[DOWN]'}")
    print(f"\nREQUIRED parameters ({len(REQUIRED_PARAMS)}):")
    for p in REQUIRED_PARAMS:
        print(f"  - {p}: {GENERATION_PARAMS.get(p, '')}")
    print(f"\nALL available parameters ({len(GENERATION_PARAMS)}):")
    for p, desc in GENERATION_PARAMS.items():
        req = " [REQUIRED]" if p in REQUIRED_PARAMS else ""
        print(f"  - {p}{req}: {desc}")
