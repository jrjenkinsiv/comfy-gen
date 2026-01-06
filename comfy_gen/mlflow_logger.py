"""
MLflow experiment logging for ComfyGen.

Standardized schema ensures ALL experiments capture the same parameters.
"""
import mlflow
from typing import Optional
import sys

MLFLOW_URI = "http://192.168.1.162:5001"
DEFAULT_EXPERIMENT = "comfy-gen-nsfw"

# Required parameters - every experiment MUST have these
REQUIRED_PARAMS = [
    "checkpoint",
    "workflow", 
    "steps",
    "cfg",
    "width",
    "height",
    "sampler",
]

# Optional but recommended parameters
OPTIONAL_PARAMS = [
    "loras",           # Comma-separated: "add_detail:0.4,more_details:0.3"
    "prompt",          # Full positive prompt
    "negative_prompt", # Full negative prompt  
    "seed",            # Generation seed
    "ethnicity",       # Subject ethnicity
    "cup_size",        # Breast size if applicable
    "freckles",        # Freckle setting
    "expression",      # Facial expression
    "scene",           # Scene description
    "session",         # Session date/name
]


def check_mlflow_health() -> bool:
    """Check if MLflow is reachable."""
    import requests
    try:
        resp = requests.get(f"{MLFLOW_URI}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def log_experiment(
    run_name: str,
    image_url: str,
    params: dict,
    validation_score: float,
    user_rating: int,
    feedback: str,
    favorite: bool = False,
    experiment_name: str = DEFAULT_EXPERIMENT,
) -> Optional[str]:
    """
    Log an experiment to MLflow with standardized schema.
    
    Args:
        run_name: Name for this run (e.g., "redhead_handjob_v1")
        image_url: MinIO URL of generated image
        params: Dict of ALL generation parameters
        validation_score: Automated validation score (0-1)
        user_rating: User rating (1-5)
        feedback: User feedback text
        favorite: Mark as favorite
        experiment_name: MLflow experiment name
        
    Returns:
        Run ID if successful, None if failed
    """
    # Check required params
    missing = [p for p in REQUIRED_PARAMS if p not in params]
    if missing:
        print(f"[WARN] Missing required params: {missing}")
        print("       Add them to ensure complete experiment tracking!")
    
    # Check MLflow health
    if not check_mlflow_health():
        print("[ERROR] MLflow not reachable at {MLFLOW_URI}")
        print("        Try: ssh cerebro 'printf \"babyseal\\n\" | sudo -S pmset -a displaysleep 0 sleep 0 disksleep 0 powernap 0'")
        return None
    
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run(run_name=run_name) as run:
            # Log ALL params (required + optional)
            mlflow.log_params(params)
            
            # Log metrics
            mlflow.log_metric("validation_score", validation_score)
            mlflow.log_metric("user_rating", user_rating)
            
            # Log tags
            mlflow.set_tag("user_feedback", feedback)
            mlflow.set_tag("image_url", image_url)
            if favorite:
                mlflow.set_tag("favorite", "true")
            
            print(f"[OK] Logged {run_name} to MLflow")
            return run.info.run_id
            
    except Exception as e:
        print(f"[ERROR] Failed to log to MLflow: {e}")
        return None


def log_favorite(
    run_name: str,
    image_url: str,
    params: dict,
    feedback: str = "FAVORITE",
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
    )


# Example usage template
EXAMPLE = """
from comfy_gen.mlflow_logger import log_experiment, log_favorite

# Full experiment logging
log_experiment(
    run_name="redhead_handjob_v1",
    image_url="http://192.168.1.215:9000/comfy-gen/...",
    params={
        # Required
        "checkpoint": "pornmasterProPony_realismV1",
        "workflow": "pornmaster-pony-stacked-realism.json",
        "steps": 70,
        "cfg": 9,
        "width": 768,
        "height": 1280,
        "sampler": "euler_ancestral",
        # Optional but recommended
        "loras": "add_detail:0.4,more_details:0.3,Pale_Skin_SDXL:0.4,realcumv6.55:0.6,airoticart_penis:0.5",
        "prompt": "score_9, (beautiful redhead:1.4)...",
        "negative_prompt": "score_6, bad quality...",
        "seed": 12345,
        "ethnicity": "redhead",
        "cup_size": "DD",
        "expression": "surprised",
        "session": "2026-01-06",
    },
    validation_score=0.672,
    user_rating=4,
    feedback="Almost there with dick realism",
)

# Quick favorite logging
log_favorite(
    run_name="best_sde_lora",
    image_url="http://192.168.1.215:9000/comfy-gen/...",
    params={...all params...},
    feedback="One of the best so far",
)
"""

if __name__ == "__main__":
    print("MLflow Logger for ComfyGen")
    print(f"URI: {MLFLOW_URI}")
    print(f"Health: {'OK' if check_mlflow_health() else 'DOWN'}")
    print(f"\nRequired params: {REQUIRED_PARAMS}")
    print(f"Optional params: {OPTIONAL_PARAMS}")
