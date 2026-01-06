# Pre-flight Health Checks

## Overview

The massive experiment framework now includes pre-flight health checks to prevent wasted compute time when services are down. This addresses the issue where 232 out of 250 experiments (92.8%) failed due to an undetected ComfyUI crash.

## Usage

### Basic Usage

Run health checks before starting experiments:

```bash
python3 scripts/massive_experiment_framework.py --count 250 --pre-flight
```

### Without Pre-flight Checks

If you want to skip the health checks (not recommended for long runs):

```bash
python3 scripts/massive_experiment_framework.py --count 250
```

## Features

### Pre-flight Health Checks

- **ComfyUI Health**: Checks if ComfyUI is responding at `http://192.168.1.215:8188/system_stats`
- **MinIO Health**: Checks if MinIO is responding at `http://192.168.1.215:9000/minio/health/live`
- **Auto-retry**: If a service is down, waits 30 seconds and retries up to 3 times
- **Clear Errors**: If services fail health checks, the script aborts with clear error messages

### Periodic Health Checks

During long experiment runs, the framework automatically checks service health:

- **Frequency**: Every 10 experiments
- **Auto-abort**: If services are down, the run stops immediately
- **Resume Support**: Error message shows how to resume (e.g., `--start-from 120`)

### MLflow Integration

Health check results are logged to MLflow:

- Timestamp of health check
- ComfyUI status and message
- MinIO status and message
- Logged both at pre-flight and periodic checks

## Configuration

Health check parameters can be adjusted in `scripts/massive_experiment_framework.py`:

```python
HEALTH_CHECK_TIMEOUT = 5  # seconds
HEALTH_CHECK_RETRIES = 3
HEALTH_CHECK_RETRY_DELAY = 30  # seconds
PERIODIC_HEALTH_CHECK_INTERVAL = 10  # Check every N experiments
```

## Example Output

### Successful Pre-flight Check

```
======================================================================
MASSIVE EXPERIMENT FRAMEWORK
======================================================================

======================================================================
PRE-FLIGHT HEALTH CHECKS
======================================================================

[INFO] Running health checks (attempt 1/3)...
[OK] ComfyUI is healthy
[OK] MinIO is healthy

[OK] All services are healthy. Proceeding with experiments...
```

### Failed Pre-flight Check

```
======================================================================
PRE-FLIGHT HEALTH CHECKS
======================================================================

[INFO] Running health checks (attempt 1/3)...
[ERROR] Cannot connect to ComfyUI server
[ERROR] MinIO health check timed out after 5s
[WARN] Health checks failed. Retrying in 30s...

[INFO] Running health checks (attempt 2/3)...
[ERROR] Cannot connect to ComfyUI server
[ERROR] MinIO health check timed out after 5s
[WARN] Health checks failed. Retrying in 30s...

[INFO] Running health checks (attempt 3/3)...
[ERROR] Cannot connect to ComfyUI server
[ERROR] Cannot connect to MinIO server

======================================================================
[ERROR] PRE-FLIGHT CHECKS FAILED
======================================================================

One or more services are not healthy:
  - ComfyUI: Cannot connect to ComfyUI server
  - MinIO: Cannot connect to MinIO server

Aborting experiment run. Please fix the issues and try again.
```

### Periodic Check During Run

```
[100/250] exp_0099: missionary_pov
  Subject: japanese curvy late_twenties
  Setting: bedroom_luxury
  Tech: dpmpp_2m s=80 cfg=7.5 sched=karras
  LoRAs: NsfwPovAllIn@0.5+zy_AmateurS@0.3

[INFO] Periodic health check at experiment 100...

[INFO] Running health checks (attempt 1/3)...
[OK] ComfyUI is healthy
[OK] MinIO is healthy
[OK] Periodic health check passed. Continuing...
```

### Periodic Check Failure

```
[120/250] exp_0119: doggy_pov
  ...

[INFO] Periodic health check at experiment 120...

[INFO] Running health checks (attempt 1/3)...
[ERROR] Cannot connect to ComfyUI server
[OK] MinIO is healthy
[WARN] Health checks failed. Retrying in 30s...
...

======================================================================
[ERROR] PERIODIC HEALTH CHECK FAILED
======================================================================

Services are not healthy:
  - ComfyUI: Cannot connect to ComfyUI server

Aborting after 120 experiments.
Use --start-from 120 to resume after fixing the issues.
```

## Troubleshooting

### Service Not Responding

If health checks fail:

1. Check if ComfyUI is running: `ssh moira "tasklist | findstr python"`
2. Check if MinIO is running: `curl http://192.168.1.215:9000/minio/health/live`
3. Restart services if needed
4. Re-run with `--pre-flight` to verify services are healthy

### Resuming After Failure

If a periodic health check fails mid-run:

```bash
# Fix the services, then resume from where it stopped
python3 scripts/massive_experiment_framework.py --count 250 --start-from 120 --pre-flight
```

## Best Practices

1. **Always use `--pre-flight` for long runs** (50+ experiments)
2. **Monitor the first few periodic checks** to ensure services remain stable
3. **Check MLflow logs** for health check history across runs
4. **Adjust `PERIODIC_HEALTH_CHECK_INTERVAL`** based on your service stability
   - More frequent checks (e.g., every 5 experiments) if services are unstable
   - Less frequent checks (e.g., every 20 experiments) if services are very stable
