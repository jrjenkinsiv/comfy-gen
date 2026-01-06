# Running Experiments

**Last updated:** 2026-01-06

Guide to running batch experiments for image generation parameter exploration.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Service Recovery](#service-recovery)
- [Image Upload Flow](#image-upload-flow)
- [Available Scripts](#available-scripts)
- [Running a Massive Experiment](#running-a-massive-experiment)
- [Retrying Failed Experiments](#retrying-failed-experiments)
- [Viewing Results](#viewing-results)
- [MLflow Integration](#mlflow-integration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Ensure ComfyUI is running on moira
curl -s http://192.168.1.215:8188/system_stats | python3 -c "import json,sys; print('OK' if json.load(sys.stdin) else 'FAIL')"

# 2. Run a small batch experiment (5 images)
cd /Users/jrjenkinsiv/Development/comfy-gen
python3 scripts/massive_experiment_framework.py --count 5 --seed 42

# 3. Check results in Gallery
open http://192.168.1.215:8080
```

---

## Service Recovery

After restarting moira, services need to be manually started. Use `start_all_services.py` to restore all services.

### Quick Recovery

```bash
# SSH to moira and start all services
ssh moira "C:\Users\jrjen\comfy\.venv\Scripts\python.exe C:\Users\jrjen\comfy-gen\scripts\start_all_services.py"
```

### Check Service Status

```bash
# Check if services are running
ssh moira "C:\Users\jrjen\comfy\.venv\Scripts\python.exe C:\Users\jrjen\comfy-gen\scripts\start_all_services.py --status"
```

Expected output when services are healthy:
```
============================================================
ComfyGen Services Status
============================================================

ComfyUI Server:
  Status: [OK] Running
  URL:    http://192.168.1.215:8188

MinIO Server:
  Status: [OK] Running
  URL:    http://192.168.1.215:9000
  Console: http://192.168.1.215:9001

============================================================
```

### Start Individual Services

```bash
# Start only ComfyUI
ssh moira "C:\Users\jrjen\comfy\.venv\Scripts\python.exe C:\Users\jrjen\comfy-gen\scripts\start_all_services.py --comfyui-only"

# Start only MinIO
ssh moira "C:\Users\jrjen\comfy\.venv\Scripts\python.exe C:\Users\jrjen\comfy-gen\scripts\start_all_services.py --minio-only"
```

### Service Details

| Service | Port | Health Check | Log File |
|---------|------|--------------|----------|
| ComfyUI | 8188 | `/system_stats` | `C:\Users\jrjen\comfyui_server.log` |
| MinIO | 9000 | `/minio/health/live` | `C:\Users\jrjen\minio_server.log` |
| MinIO Console | 9001 | Web UI | Same as MinIO |

### Troubleshooting Service Startup

**Service starts but API not responding:**
- Check log files for errors
- ComfyUI: `type C:\Users\jrjen\comfyui_server.log`
- MinIO: `type C:\Users\jrjen\minio_server.log`

**Service fails to start:**
- Verify paths exist (script will report missing paths)
- Check for port conflicts (another process using 8188 or 9000)
- Try starting services individually with `--comfyui-only` or `--minio-only`

**ComfyUI still not responding after start:**
- Wait 30-60 seconds for initialization
- Check VRAM availability: `nvidia-smi`
- Restart with `scripts/restart_comfyui.py`

**MLflow and Gallery:**
- These services are managed separately via `scripts/moira_services/start_services.py`
- They typically need less frequent restarts

---

## Image Upload Flow

**IMPORTANT:** Images are automatically uploaded to MinIO by `generate.py`. No separate uploader script is needed.

```
generate.py execution
    │
    ├─► ComfyUI generates image
    │
    ├─► Image saved to local path (--output)
    │
    └─► Automatic upload to MinIO
        http://192.168.1.215:9000/comfy-gen/<timestamp>_<filename>.png
            │
            └─► Gallery server (cerebro) displays from MinIO
                http://192.168.1.215:8080
```

**Why previous uploader script existed:**
The `minio_uploader.py` was created when we thought `generate.py` wasn't uploading. In fact, `generate.py` always uploads on success. The separate uploader is not needed for normal operation.

---

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `massive_experiment_framework.py` | **PRIMARY** - Comprehensive parameter sweep | `--count N --seed S` |
| `batch_experiments.py` | Simple batch runner | `--count N` |
| `batch_pony_hq.py` | High-quality Pony Realism batches | `python3 scripts/batch_pony_hq.py COUNT SEED` |
| `batch_oral_refined.py` | Oral/handjob focused | Direct run |
| `batch_final_refined.py` | Cumshot/oral/handjob refined | Direct run |

---

## Running a Massive Experiment

The `massive_experiment_framework.py` is the most comprehensive experiment runner. It explores:

- **50+ scenarios:** solo, oral, sex positions, cumshots, lesbian, etc.
- **19 ethnicities:** Asian, European, African, etc.
- **7 body types:** petite, curvy, athletic, etc.
- **18 settings:** bedroom, beach, office, etc.
- **8 samplers:** euler, dpmpp_sde, dpmpp_2m, etc.
- **5 step ranges:** 30, 50, 80, 120, 150
- **10 LoRA presets:** nsfw_detailed, cumshot_heavy, etc.

### Basic Run

```bash
cd /Users/jrjenkinsiv/Development/comfy-gen

# Dry run to see what will be generated
python3 scripts/massive_experiment_framework.py --count 10 --dry-run

# Actual run (10 experiments)
python3 scripts/massive_experiment_framework.py --count 10 --seed 42
```

### Long Run (overnight)

```bash
# Run 200 experiments (expect ~5-6 hours)
nohup python3 scripts/massive_experiment_framework.py --count 200 --seed 42 \
    > /tmp/experiment_run.log 2>&1 &

# Monitor progress
tail -f /tmp/experiment_run.log

# Check generated images
ls /tmp/massive_experiment/*.png | wc -l
```

### Output Structure

```
/tmp/massive_experiment/
├── 20260105_220955_exp_0001_scenario_ethnicity.png
├── 20260105_220955_exp_0002_scenario_ethnicity.png
├── ...
├── metadata/
│   ├── exp_0001.json    # Full config + result
│   ├── exp_0002.json
│   └── ...
└── minio_uploads.json   # Upload tracking (if uploader used)
```

### Metadata Format

Each `exp_NNNN.json` contains:

```json
{
  "config": {
    "experiment_id": "exp_0005",
    "ethnicity": "middle_eastern",
    "body_type": "busty_slim",
    "scenario_name": "nude_portrait",
    "scenario_category": "solo_female",
    "sampler": "euler",
    "steps": 120,
    "cfg": 6.5,
    "lora_preset_name": "amateur_grainy",
    "loras": [["zy_AmateurStyle_v2.safetensors", 0.5], ...],
    "full_positive_prompt": "...",
    "full_negative_prompt": "..."
  },
  "result": {
    "success": true,
    "minio_url": "http://192.168.1.215:9000/comfy-gen/...",
    "validation_score": 0.682,
    "generation_time_seconds": 85.3
  }
}
```

---

## Retrying Failed Experiments

If experiments fail (ComfyUI crash, network issues), retry failed ones:

### Manual Retry Script

```bash
# Create retry script from failed experiments
cd /Users/jrjenkinsiv/Development/comfy-gen

python3 << 'EOF'
import json
from pathlib import Path

metadata_dir = Path("/tmp/massive_experiment/metadata")
failed = []

for f in sorted(metadata_dir.glob("*.json")):
    data = json.load(open(f))
    if not data["result"]["success"]:
        failed.append(data["config"])

print(f"Found {len(failed)} failed experiments")

# Save for retry
with open("/tmp/failed_experiments.json", "w") as f:
    json.dump(failed, f, indent=2)
EOF

# Check count
python3 -c "import json; print(len(json.load(open('/tmp/failed_experiments.json'))))"
```

### Re-run Failed Experiments

```bash
# Re-run each failed config
python3 << 'EOF'
import json
import subprocess
import sys
from pathlib import Path

failed = json.load(open("/tmp/failed_experiments.json"))
print(f"Retrying {len(failed)} experiments...")

for i, config in enumerate(failed):
    print(f"\n[{i+1}/{len(failed)}] {config['experiment_id']}: {config['scenario_name']}")
    
    cmd = [
        sys.executable, "generate.py",
        "--workflow", config["workflow_file"],
        "--prompt", config["full_positive_prompt"],
        "--negative-prompt", config["full_negative_prompt"],
        "--steps", str(config["steps"]),
        "--cfg", str(config["cfg"]),
        "--sampler", config["sampler"],
        "--scheduler", config["scheduler"],
        "--output", f"/tmp/retry_{config['experiment_id']}.png"
    ]
    
    for lora_name, strength in config["loras"]:
        cmd.extend(["--lora", f"{lora_name}:{strength}"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("  OK" if result.returncode == 0 else f"  FAILED: {result.stderr[-200:]}")
EOF
```

---

## Viewing Results

### Gallery (Recommended)

All successfully generated images appear in the Gallery automatically:

```bash
open http://192.168.1.215:8080
```

### MinIO Direct Access

```bash
# List all images
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+\.png' | tail -20

# Open specific image
open "http://192.168.1.215:9000/comfy-gen/20260105_221520_filename.png"
```

### Local Files

```bash
# List local experiment images
ls -la /tmp/massive_experiment/*.png

# Open in Preview (macOS)
open /tmp/massive_experiment/20260105_220955_exp_0005_nude_portrait_middle_eastern.png
```

---

## MLflow Integration

The experiment framework logs to MLflow for tracking:

### View Experiment Runs

```bash
open http://192.168.1.162:5001
```

Look for experiment: `comfy-gen-massive-experiment`

### Logged Parameters

Each run logs:
- `experiment_id`, `scenario`, `ethnicity`
- `sampler`, `steps`, `cfg`
- `lora_preset`, individual LoRA names/strengths
- `success`, `generation_time`
- `minio_url` (if successful)

### Query Results

```python
import mlflow

mlflow.set_tracking_uri("http://192.168.1.162:5001")
experiment = mlflow.get_experiment_by_name("comfy-gen-massive-experiment")

runs = mlflow.search_runs(
    experiment_ids=[experiment.experiment_id],
    filter_string="params.success = 'True'",
    order_by=["params.validation_score DESC"]
)

print(runs[["params.scenario", "params.ethnicity", "params.sampler", "params.steps"]])
```

---

## Troubleshooting

### Services Not Running After Restart

**Problem:** After restarting moira, ComfyUI and MinIO need manual start.

**Solution:** Use the service recovery script:

```bash
# Start all services
ssh moira "C:\Users\jrjen\comfy\.venv\Scripts\python.exe C:\Users\jrjen\comfy-gen\scripts\start_all_services.py"

# Or check status first
ssh moira "C:\Users\jrjen\comfy\.venv\Scripts\python.exe C:\Users\jrjen\comfy-gen\scripts\start_all_services.py --status"
```

See [Service Recovery](#service-recovery) section for detailed instructions.

### ComfyUI Not Responding

```bash
# Check status
curl -s http://192.168.1.215:8188/system_stats || echo "OFFLINE"

# Restart ComfyUI using service script
ssh moira "C:\Users\jrjen\comfy\.venv\Scripts\python.exe C:\Users\jrjen\comfy-gen\scripts\start_all_services.py --comfyui-only"
```

### High Failure Rate

If >50% experiments fail:

1. **Check ComfyUI health** before starting
2. **Reduce batch size** - run 50 at a time instead of 200
3. **Add delays** - modify script to wait 5s between generations
4. **Check VRAM** - some LoRA combinations exhaust GPU memory

### Images Not in Gallery

1. **Check MinIO upload succeeded:**
   ```bash
   curl -s http://192.168.1.215:9000/comfy-gen/ | grep -c "\.png"
   ```

2. **Check generate.py output** for upload errors:
   ```
   [OK] Uploaded ... to MinIO as ...
   [ERROR] MinIO error: ...
   ```

3. **Verify MinIO is running:**
   ```bash
   curl -s http://192.168.1.215:9000/minio/health/live
   ```

### Empty Error Messages in Metadata

The experiment script captures stderr, but ComfyUI errors may go to stdout. Check the terminal output or run with `2>&1 | tee logfile.txt`.

---

## Best Practices

1. **Always check ComfyUI status** before starting long runs
2. **Use `--dry-run`** first to verify experiment configuration
3. **Start with small counts** (5-10) to test, then scale up
4. **Keep seed consistent** for reproducibility: `--seed 42`
5. **Monitor the log** during long runs: `tail -f /tmp/experiment_run.log`
6. **Review Gallery** periodically to catch issues early

---

## Related Documentation

- [NSFW_GUIDE.md](NSFW_GUIDE.md) - Prompting and LoRA configuration
- [USAGE.md](USAGE.md) - General CLI usage
- [LORA_GUIDE.md](LORA_GUIDE.md) - LoRA selection and verification
- [QUALITY_SYSTEM.md](QUALITY_SYSTEM.md) - Validation scoring
