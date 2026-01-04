#!/usr/bin/env python3
"""Tests for generate.py error handling and validation."""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import generate
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_check_server_availability_success():
    """Test server availability check when server is reachable."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = generate.check_server_availability()
        assert result is True
        print("[OK] Server availability check succeeds when server is up")


def test_check_server_availability_connection_error():
    """Test server availability check when server is unreachable."""
    with patch('requests.get') as mock_get:
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        result = generate.check_server_availability()
        assert result is False
        print("[OK] Server availability check fails on connection error")


def test_check_server_availability_timeout():
    """Test server availability check when request times out."""
    with patch('requests.get') as mock_get:
        import requests
        mock_get.side_effect = requests.Timeout("Timeout")
        
        result = generate.check_server_availability()
        assert result is False
        print("[OK] Server availability check fails on timeout")


def test_get_available_models_success():
    """Test getting available models from API."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "CheckpointLoaderSimple": {
                "input": {
                    "required": {
                        "ckpt_name": [["model1.safetensors", "model2.safetensors"]]
                    }
                }
            },
            "LoraLoader": {
                "input": {
                    "required": {
                        "lora_name": [["lora1.safetensors", "lora2.safetensors"]]
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        
        models = generate.get_available_models()
        assert models is not None
        assert "checkpoints" in models
        assert "loras" in models
        assert "model1.safetensors" in models["checkpoints"]
        assert "lora1.safetensors" in models["loras"]
        print("[OK] get_available_models extracts models correctly")


def test_find_model_fallbacks():
    """Test model fallback suggestions."""
    available_models = {
        "checkpoints": [
            "sd15-v1-5.safetensors",
            "sd15-inpainting.safetensors",
            "sdxl-base-1.0.safetensors",
            "flux-dev.safetensors"
        ]
    }
    
    # Test exact substring match
    suggestions = generate.find_model_fallbacks(
        "sd15",
        available_models,
        "checkpoints"
    )
    assert len(suggestions) > 0
    assert any("sd15" in s.lower() for s in suggestions)
    print("[OK] find_model_fallbacks suggests similar models")
    
    # Test no matches
    suggestions = generate.find_model_fallbacks(
        "nonexistent-model",
        available_models,
        "checkpoints"
    )
    # May return empty or partial matches
    print(f"[OK] find_model_fallbacks handles no matches: {len(suggestions)} suggestions")


def test_validate_workflow_models_valid():
    """Test workflow validation with valid models."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "model1.safetensors"
            }
        }
    }
    
    available_models = {
        "checkpoints": ["model1.safetensors", "model2.safetensors"]
    }
    
    is_valid, missing, suggestions = generate.validate_workflow_models(workflow, available_models)
    assert is_valid is True
    assert len(missing) == 0
    print("[OK] validate_workflow_models passes for valid workflow")


def test_validate_workflow_models_missing():
    """Test workflow validation with missing models."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "missing-model.safetensors"
            }
        }
    }
    
    available_models = {
        "checkpoints": ["model1.safetensors", "model2.safetensors"]
    }
    
    is_valid, missing, suggestions = generate.validate_workflow_models(workflow, available_models)
    assert is_valid is False
    assert len(missing) == 1
    assert missing[0] == ("checkpoint", "missing-model.safetensors")
    print("[OK] validate_workflow_models detects missing models")


def test_queue_workflow_retry_on_server_error():
    """Test that queue_workflow retries on server errors."""
    workflow = {"test": "workflow"}
    
    with patch('requests.post') as mock_post:
        # First call fails with 503, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503
        mock_response_fail.text = "Service Unavailable"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"prompt_id": "test123"}
        
        mock_post.side_effect = [mock_response_fail, mock_response_success]
        
        with patch('time.sleep'):  # Skip actual sleep
            result = generate.queue_workflow(workflow, retry=True)
        
        assert result == "test123"
        assert mock_post.call_count == 2
        print("[OK] queue_workflow retries on server error")


def test_queue_workflow_no_retry_on_client_error():
    """Test that queue_workflow doesn't retry on client errors."""
    workflow = {"test": "workflow"}
    
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        result = generate.queue_workflow(workflow, retry=True)
        
        assert result is None
        assert mock_post.call_count == 1  # No retry
        print("[OK] queue_workflow doesn't retry on client error")


def test_exit_codes():
    """Test that exit code constants are defined."""
    assert hasattr(generate, 'EXIT_SUCCESS')
    assert hasattr(generate, 'EXIT_FAILURE')
    assert hasattr(generate, 'EXIT_CONFIG_ERROR')
    assert generate.EXIT_SUCCESS == 0
    assert generate.EXIT_FAILURE == 1
    assert generate.EXIT_CONFIG_ERROR == 2
    print("[OK] Exit codes are properly defined")


def test_load_workflow_file_not_found():
    """Test workflow loading with nonexistent file."""
    try:
        generate.load_workflow("/nonexistent/workflow.json")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        print("[OK] load_workflow raises FileNotFoundError for missing file")


def test_load_workflow_invalid_json():
    """Test workflow loading with invalid JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("invalid json {")
        temp_path = f.name
    
    try:
        try:
            generate.load_workflow(temp_path)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            print("[OK] load_workflow raises JSONDecodeError for invalid JSON")
    finally:
        os.unlink(temp_path)


def test_find_prompt_nodes_sd15():
    """Test finding prompt nodes in SD 1.5 workflow."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "Load Checkpoint"}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test"},
            "_meta": {"title": "Positive Prompt"}
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ""},
            "_meta": {"title": "Negative Prompt"}
        }
    }
    
    pos_node, neg_node = generate.find_prompt_nodes(workflow)
    assert pos_node == "2", f"Expected positive node '2', got '{pos_node}'"
    assert neg_node == "3", f"Expected negative node '3', got '{neg_node}'"
    print("[OK] find_prompt_nodes correctly identifies SD 1.5 workflow nodes")


def test_find_prompt_nodes_wan22():
    """Test finding prompt nodes in Wan 2.2 workflow."""
    workflow = {
        "1": {
            "class_type": "UNETLoader",
            "_meta": {"title": "Load Diffusion Model"}
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "motion prompt"},
            "_meta": {"title": "Motion Prompt"}
        }
    }
    
    pos_node, neg_node = generate.find_prompt_nodes(workflow)
    assert pos_node == "3", f"Expected positive node '3', got '{pos_node}'"
    assert neg_node is None, f"Expected no negative node, got '{neg_node}'"
    print("[OK] find_prompt_nodes correctly identifies Wan 2.2 workflow nodes")


def test_find_prompt_nodes_fallback():
    """Test fallback to first CLIPTextEncode node."""
    workflow = {
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "first clip node"},
            "_meta": {"title": "Some CLIP Node"}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "second clip node"},
            "_meta": {"title": "Another CLIP Node"}
        }
    }
    
    pos_node, neg_node = generate.find_prompt_nodes(workflow)
    assert pos_node == "5", f"Expected positive node '5' (first CLIP), got '{pos_node}'"
    assert neg_node is None, f"Expected no negative node, got '{neg_node}'"
    print("[OK] find_prompt_nodes falls back to first CLIPTextEncode")


def test_get_default_negative_prompt_sd15():
    """Test default negative prompt for SD 1.5 workflows."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd15.safetensors"}
        }
    }
    
    default_neg = generate.get_default_negative_prompt(workflow)
    assert default_neg != "", "SD 1.5 workflow should have default negative prompt"
    assert "bad quality" in default_neg.lower(), "Default should contain 'bad quality'"
    assert "blurry" in default_neg.lower(), "Default should contain 'blurry'"
    print(f"[OK] get_default_negative_prompt returns SD 1.5 default: '{default_neg[:50]}...'")


def test_get_default_negative_prompt_wan22():
    """Test default negative prompt for Wan 2.2 workflows."""
    workflow = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {}
        }
    }
    
    default_neg = generate.get_default_negative_prompt(workflow)
    assert default_neg == "", "Wan 2.2 workflow should have empty default negative prompt"
    print("[OK] get_default_negative_prompt returns empty for Wan 2.2")


def test_modify_prompt_with_negative():
    """Test modify_prompt with custom negative prompt."""
    workflow = {
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "old positive"},
            "_meta": {"title": "Positive Prompt"}
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "old negative"},
            "_meta": {"title": "Negative Prompt"}
        }
    }
    
    modified = generate.modify_prompt(workflow, "new positive", "new negative")
    
    assert modified["2"]["inputs"]["text"] == "new positive"
    assert modified["3"]["inputs"]["text"] == "new negative"
    print("[OK] modify_prompt updates both positive and negative prompts")


def test_modify_prompt_default_negative():
    """Test modify_prompt with default negative prompt."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "old positive"},
            "_meta": {"title": "Positive Prompt"}
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ""},
            "_meta": {"title": "Negative Prompt"}
        }
    }
    
    # Call without negative prompt - should apply default
    modified = generate.modify_prompt(workflow, "test prompt", "")
    
    assert modified["2"]["inputs"]["text"] == "test prompt"
    # Should get default negative for SD workflows
    default_neg = modified["3"]["inputs"]["text"]
    assert default_neg != "", "Should apply default negative prompt"
    assert "bad quality" in default_neg.lower()
    print(f"[OK] modify_prompt applies default negative: '{default_neg[:50]}...'")


def test_modify_prompt_no_negative_node():
    """Test modify_prompt with workflow that has no negative node."""
    workflow = {
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "old prompt"},
            "_meta": {"title": "Motion Prompt"}
        }
    }
    
    # Should not crash when negative prompt provided but no node exists
    modified = generate.modify_prompt(workflow, "new prompt", "negative prompt")
    
    assert modified["3"]["inputs"]["text"] == "new prompt"
    print("[OK] modify_prompt handles missing negative node gracefully")


if __name__ == "__main__":
    print("Running generate.py tests...\n")
    
    tests = [
        test_check_server_availability_success,
        test_check_server_availability_connection_error,
        test_check_server_availability_timeout,
        test_get_available_models_success,
        test_find_model_fallbacks,
        test_validate_workflow_models_valid,
        test_validate_workflow_models_missing,
        test_queue_workflow_retry_on_server_error,
        test_queue_workflow_no_retry_on_client_error,
        test_exit_codes,
        test_load_workflow_file_not_found,
        test_load_workflow_invalid_json,
        test_find_prompt_nodes_sd15,
        test_find_prompt_nodes_wan22,
        test_find_prompt_nodes_fallback,
        test_get_default_negative_prompt_sd15,
        test_get_default_negative_prompt_wan22,
        test_modify_prompt_with_negative,
        test_modify_prompt_default_negative,
        test_modify_prompt_no_negative_node,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\nRunning {test.__name__}...")
            test()
            passed += 1
        except Exception as e:
            print(f"[FAILED] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'='*60}")
    
    sys.exit(0 if failed == 0 else 1)
