# ComfyGen Testing Guide

## Overview

ComfyGen uses pytest for automated testing with three test categories:
1. **Unit Tests** - Fast, mocked tests for individual modules
2. **Integration Tests** - Tests that verify connectivity to real services
3. **Manual Tests** - End-to-end generation workflows requiring human verification

## Test Structure

```
tests/
├── conftest.py                      # Pytest configuration
├── test_clients/                    # Client module tests (mocked)
│   ├── test_comfyui_client.py      # Mock HTTP/WS responses
│   ├── test_minio_client.py        # Mock S3 responses
│   └── test_civitai_client.py      # Mock API responses
├── test_utils/                      # Utility module tests (mocked)
│   ├── test_validation.py          # Validation logic
│   ├── test_quality.py             # Quality scoring
│   └── test_mlflow_logger.py       # MLflow logging (mocked)
├── test_generate.py                 # Main generation script tests
└── integration/                     # Integration tests (real services)
    ├── test_comfyui_connection.py  # Verify moira:8188 reachable
    ├── test_minio_connection.py    # Verify moira:9000 reachable
    ├── test_mlflow_connection.py   # Verify cerebro:5001 reachable
    └── test_simple_generation.py   # End-to-end SD 1.5 generation
```

## Running Tests

### Local Development

```bash
# Run all unit tests (fast, no external dependencies)
pytest tests/ -v -m "not integration"

# Run specific test file
pytest tests/test_clients/test_comfyui_client.py -v

# Run tests with coverage
pytest tests/ -v -m "not integration" --cov=clients --cov=utils --cov-report=html

# Run integration tests (requires cerebro/moira connectivity)
pytest tests/integration/ -v -m integration
```

### CI Environment

CI runs on GitHub-hosted runners (ubuntu-latest) which cannot reach moira/cerebro.
Integration tests are automatically skipped in CI.

```yaml
# In .github/workflows/ci.yml
pytest tests/ -v -m "not integration"
```

## Test Categories

### Unit Tests (`-m "not integration"`)

**Purpose:** Validate logic without external dependencies  
**Speed:** Fast (&lt;5 seconds total)  
**Mocking:** All HTTP requests, file I/O, and external services mocked

**Examples:**
- `test_comfyui_client.py` - Mock requests to ComfyUI API
- `test_minio_client.py` - Mock S3/MinIO operations
- `test_validation.py` - Test prompt validation logic
- `test_mlflow_logger.py` - Mock MLflow tracking calls

### Integration Tests (`@pytest.mark.integration`)

**Purpose:** Verify real service connectivity  
**Speed:** Slower (network-dependent)  
**Environment:** Requires cerebro runner or local network access

**Infrastructure:**
- **ComfyUI:** moira (192.168.1.215:8188)
- **MinIO:** moira (192.168.1.215:9000)
- **MLflow:** cerebro (192.168.1.162:5001)

**Examples:**
```python
import pytest

@pytest.mark.integration
def test_comfyui_reachable():
    """Verify ComfyUI server is reachable."""
    from clients.comfyui_client import ComfyUIClient
    client = ComfyUIClient()
    assert client.check_availability(), "ComfyUI server not reachable"
```

**Running on cerebro:**
```bash
# SSH to cerebro and run integration tests
ssh cerebro
cd /path/to/comfy-gen
pytest tests/integration/ -v -m integration
```

### Manual Test Checklist

These tests require human verification and cannot be automated:

#### Image Generation Tests

- [ ] **flux-dev.json workflow**
  ```bash
  python generate.py --workflow workflows/flux-dev.json \
      --prompt "a sunset over mountains" \
      --output /tmp/test_flux.png
  ```
  - [ ] Image generates successfully
  - [ ] Output matches prompt
  - [ ] MinIO upload successful
  - [ ] URL accessible: `http://192.168.1.215:9000/comfy-gen/<filename>.png`

- [ ] **SD 1.5 workflow with LoRAs**
  ```bash
  python generate.py --workflow workflows/majicmix-realism.json \
      --prompt "portrait of a woman, detailed skin" \
      --loras "add_detail:0.5,more_details:0.3" \
      --output /tmp/test_lora.png
  ```
  - [ ] LoRAs applied correctly
  - [ ] Generation completes without errors

#### Video Generation Tests

- [ ] **wan22-t2v.json workflow**
  ```bash
  python generate.py --workflow workflows/wan22-t2v.json \
      --prompt "a person walking in a park" \
      --output /tmp/test_video.mp4
  ```
  - [ ] Video generates successfully
  - [ ] Motion coherent
  - [ ] Output uploaded to MinIO

#### MLflow Logging Tests

- [ ] **Experiment tracking**
  ```python
  from utils.mlflow_logger import log_experiment
  
  log_experiment(
      run_name="test_run",
      image_url="http://192.168.1.215:9000/comfy-gen/test.png",
      params={"checkpoint": "flux-dev", "steps": 50, "cfg": 7.5},
      validation_score=0.75,
      user_rating=4,
      feedback="Test run successful"
  )
  ```
  - [ ] Run appears in MLflow UI: `http://192.168.1.162:5001`
  - [ ] Parameters logged correctly
  - [ ] Metrics recorded

#### MCP Server Tests

- [ ] **MCP tools respond**
  ```bash
  # Test MCP server startup
  python mcp_server.py
  ```
  - [ ] Server starts without errors
  - [ ] Tools registered successfully
  - [ ] Can be called from IDE integration

## Writing New Tests

### Unit Test Template

```python
"""Tests for <module_name>."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestModuleName:
    """Tests for ModuleName class."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        obj = ModuleName()
        
        # Act
        result = obj.method()
        
        # Assert
        assert result is not None


    @patch('module.external_dependency')
    def test_with_mocking(self, mock_dependency):
        """Test with mocked external dependency."""
        # Setup mock
        mock_dependency.return_value = "mocked_value"
        
        # Test
        result = function_under_test()
        
        # Verify
        assert result == "expected"
        mock_dependency.assert_called_once()
```

### Integration Test Template

```python
"""Integration tests for <service>."""

import pytest


@pytest.mark.integration
class TestServiceIntegration:
    """Integration tests for Service (requires real service)."""

    def test_service_available(self):
        """Test service is reachable."""
        from clients.service_client import ServiceClient
        
        client = ServiceClient()
        assert client.check_availability(), "Service not reachable"


    def test_basic_operation(self):
        """Test basic service operation."""
        from clients.service_client import ServiceClient
        
        client = ServiceClient()
        result = client.simple_operation()
        assert result is not None
```

## Debugging Failed Tests

### Common Issues

1. **Import errors**
   ```bash
   # Install package in editable mode
   pip install -e .
   ```

2. **Mock not working**
   ```python
   # Use correct patch path (where it's used, not where defined)
   @patch('module_under_test.dependency')  # NOT 'dependency_module.dependency'
   ```

3. **Integration test fails in CI**
   ```python
   # Mark test properly to skip in CI
   @pytest.mark.integration
   ```

4. **Pytest not finding tests**
   ```bash
   # Ensure conftest.py exists and files match test_*.py pattern
   pytest --collect-only  # Show what pytest discovers
   ```

## Test Coverage Goals

| Module | Target Coverage | Current |
|--------|----------------|---------|
| `clients/` | 80% | TBD |
| `utils/` | 80% | TBD |
| `generate.py` | 70% | TBD |
| Integration | N/A | N/A |

## CI/CD Integration

### GitHub Actions Workflow

The CI workflow (`.github/workflows/ci.yml`) runs:

1. **Lint** - Code quality checks with ruff
2. **Type Check** - mypy static analysis (advisory)
3. **Module Validation** - Import smoke tests
4. **Unit Tests** - pytest with integration tests skipped
5. **Summary** - Aggregate results

### Test Execution in CI

```yaml
- name: Run pytest
  run: |
    pytest tests/ -v \
      -m "not integration" \
      --ignore=tests/manual_test_*.py \
      --ignore=tests/test_error_handling_manual.sh \
      --tb=short
```

### Skipping Tests

```python
# Skip test unconditionally
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass


# Skip based on condition
@pytest.mark.skipif(not DEPENDENCY_AVAILABLE, reason="Dependency not installed")
def test_with_dependency():
    pass
```

## Troubleshooting

### Tests Pass Locally but Fail in CI

- Check if test requires local network access → mark as `@pytest.mark.integration`
- Check if test writes to specific paths → use `tmpdir` fixture
- Check if test requires GPU → not available in CI

### Integration Tests Fail on cerebro

1. **Verify service status:**
   ```bash
   # ComfyUI
   curl http://192.168.1.215:8188/system_stats
   
   # MinIO
   curl http://192.168.1.215:9000/minio/health/live
   
   # MLflow
   curl http://192.168.1.162:5001/health
   ```

2. **Check cerebro can reach moira:**
   ```bash
   ssh cerebro
   ping 192.168.1.215
   curl http://192.168.1.215:8188/system_stats
   ```

3. **Verify MLflow on cerebro:**
   ```bash
   ssh cerebro
   ps aux | grep mlflow
   curl http://localhost:5001/health
   ```

### cerebro Sleep Issues

If MLflow becomes unreachable, cerebro may have slept. Wake it up:

```bash
ssh cerebro 'printf "babyseal\n" | sudo -S pmset -a displaysleep 0 sleep 0 disksleep 0 powernap 0'
```

## Resources

- **pytest docs:** https://docs.pytest.org/
- **unittest.mock:** https://docs.python.org/3/library/unittest.mock.html
- **MLflow tracking:** http://192.168.1.162:5001
- **ComfyUI API:** http://192.168.1.215:8188
- **MinIO console:** http://192.168.1.215:9000
