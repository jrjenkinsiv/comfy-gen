# Scripts Directory

This directory contains utility scripts for comfy-gen operations.

## Directory Policy

### KEEP in scripts/

**Infrastructure scripts** (permanent, reusable):
- `start_comfyui.py`, `stop_comfyui.py`, `restart_comfyui.py` - Server management
- `check_comfyui_status.py` - Health checks
- `download_*.py` - Model/LoRA downloads
- `civitai_audit.py` - LoRA catalog auditing
- `set_bucket_policy.py`, `create_bucket.py` - MinIO management
- `gallery_server.py` - Persistent service
- `smoke_test.py`, `validate_workflows.py` - CI/testing
- `backfill_metadata.py` - Data migration utilities

### MOVE to experiments/archive/scripts/

**One-off batch scripts** (ran once, kept for reference):
- `batch_*.py` - One-time experiment runs
- `massive_experiment*.py` - Large-scale tests
- `lora_strength_test.py` - Parameter sweeps
- `refine_*.py`, `iterative_enhance.py` - Iteration experiments

These are historical records, not reusable tools. They should NOT clutter the main scripts/ folder.

### DELETE candidates

Scripts that are superseded by better tooling:
- `minio_tunnel.py` - Direct access works now
- `log_experiments.py` - Superseded by mlflow_logger.py
- `test_prompts.py` - Superseded by generate.py --prompt
- `example_validation.py` - Example code, not production

## Cleanup Procedure

```bash
# Move batch scripts to archive
mkdir -p experiments/archive/scripts
mv scripts/batch_*.py experiments/archive/scripts/
mv scripts/massive_experiment*.py experiments/archive/scripts/
mv scripts/lora_strength_test.py experiments/archive/scripts/
mv scripts/refine_*.py experiments/archive/scripts/
mv scripts/iterative_enhance.py experiments/archive/scripts/
```

## Creating New Scripts

1. **Is it reusable?** → `scripts/`
2. **Is it a one-off experiment?** → Run inline or `experiments/archive/scripts/`
3. **Is it CI/testing?** → `tests/` or `scripts/` with `test_` or `validate_` prefix
