# FastAPI Generation Server

FastAPI server that wraps `generate.py` functionality, enabling typed client access for CLI, MCP, and future GUI.

## Features

- **POST /generate** - Submit generation request (returns job ID)
- **GET /generate/{id}** - Poll job status
- **GET /health** - Health check endpoint
- **WebSocket /ws/progress/{id}** - Stream ComfyUI progress
- Pydantic schemas for all request/response types
- Thread-safe in-memory job queue
- Integration with existing ComfyUI client

## Configuration

The server uses environment variables for configuration:

```bash
# MinIO endpoint (default: 192.168.1.215:9000)
export MINIO_ENDPOINT="192.168.1.215:9000"

# MinIO bucket name (default: comfy-gen)
export MINIO_BUCKET="comfy-gen"

# ComfyUI host (configured in clients/comfyui_client.py)
# Default: http://192.168.1.215:8188
```

## Quick Start

### Start the Server

```bash
# From repository root
python3 api/app.py
```

Server runs on `http://localhost:8000` by default.

### API Documentation

Once running, visit:
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Example Usage

#### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Submit generation
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a sunset over mountains",
    "negative_prompt": "blurry",
    "workflow": "flux-dev.json",
    "width": 1024,
    "height": 1024,
    "steps": 20,
    "cfg": 7.0,
    "seed": 42
  }'

# Check status (replace JOB_ID with actual ID)
curl http://localhost:8000/generate/JOB_ID
```

#### Using Python

```python
import requests
import time

# Submit generation
response = requests.post("http://localhost:8000/generate", json={
    "prompt": "a sunset over mountains",
    "width": 1024,
    "height": 1024,
    "steps": 20,
    "cfg": 7.0,
})

job_id = response.json()["id"]
print(f"Job ID: {job_id}")

# Poll for completion
while True:
    status = requests.get(f"http://localhost:8000/generate/{job_id}").json()
    print(f"Status: {status['status']} - Progress: {status['progress']:.0%}")
    
    if status["status"] == "completed":
        print(f"Image URL: {status['image_url']}")
        break
    elif status["status"] == "failed":
        print(f"Error: {status['error']}")
        break
    
    time.sleep(2)
```

#### Using WebSocket

```python
import asyncio
import json
import websockets

async def track_progress(job_id):
    async with websockets.connect(f"ws://localhost:8000/ws/progress/{job_id}") as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            
            print(f"Progress: {data['progress']:.0%} - {data['status']}")
            
            if data["status"] in ["completed", "failed"]:
                break

asyncio.run(track_progress("your-job-id"))
```

## API Reference

### POST /generate

Submit a new generation request.

**Request Body:**
```json
{
  "prompt": "string",
  "negative_prompt": "string (optional)",
  "workflow": "string (default: flux-dev.json)",
  "width": 1024,
  "height": 1024,
  "steps": 20,
  "cfg": 7.0,
  "seed": -1,
  "loras": ["lora:0.8"],
  "sampler": "string (optional)",
  "scheduler": "string (optional)"
}
```

**Response (202 Accepted):**
```json
{
  "id": "uuid",
  "status": "queued",
  "progress": 0.0,
  "image_url": null,
  "error": null
}
```

### GET /generate/{id}

Get the status of a generation job.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "status": "running",  // queued | running | completed | failed
  "progress": 0.5,
  "image_url": "http://...",  // Available when completed
  "error": "string"  // Available when failed
}
```

### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",  // healthy | degraded
  "comfyui_available": true,
  "version": "0.1.0"
}
```

### WebSocket /ws/progress/{id}

Stream real-time progress updates for a job.

**Messages:**
```json
{
  "job_id": "uuid",
  "status": "running",
  "progress": 0.5,
  "step": 10,
  "max_steps": 20,
  "message": "string (optional)",
  "image_url": "string (when completed)",
  "error": "string (when failed)"
}
```

## Development

### Running Tests

```bash
# Unit tests (mocked ComfyUI)
python3 tests/test_api.py

# Integration test (requires ComfyUI server)
pytest tests/test_api_integration.py -v

# Manual test
python3 tests/manual_test_api_server.py
```

### Code Quality

```bash
# Lint
python3 -m ruff check api/

# Format
python3 -m ruff format api/
```

## Architecture

```
api/
├── __init__.py         # Package initialization
├── app.py              # FastAPI application
├── schemas.py          # Pydantic request/response models
├── routes/
│   ├── health.py       # Health check endpoint
│   └── generate.py     # Generation endpoints
└── services/
    └── generation.py   # Generation service logic
```

**Design Principles:**
- Reuses existing `clients/comfyui_client.py`
- Wraps logic from `generate.py` without duplication
- Thread-safe in-memory job storage
- Asynchronous job execution in background threads

## Deployment

### Production Server

```bash
# Install production server
pip install uvicorn[standard]

# Run with uvicorn
uvicorn api.app:app --host 0.0.0.0 --port 8000 --workers 4

# Or with gunicorn
gunicorn api.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Limitations

- In-memory job storage (jobs lost on restart)
- No authentication/authorization
- Single server instance (no distributed job queue)
- No job history/cleanup

## Future Enhancements

- Persistent job storage (PostgreSQL, Redis)
- Job history with pagination
- Background job cleanup
- Rate limiting
- Authentication (API keys, OAuth)
- Distributed job queue (Celery, RabbitMQ)
- Metrics and monitoring
- Job cancellation endpoint
