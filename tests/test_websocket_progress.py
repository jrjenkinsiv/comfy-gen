#!/usr/bin/env python3
"""Tests for WebSocket progress tracking."""

import sys
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

# Add parent directory to path to import generate
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_progress_tracker_initialization():
    """Test ProgressTracker initialization."""
    tracker = generate.ProgressTracker("test_prompt_123")
    
    assert tracker.prompt_id == "test_prompt_123"
    assert tracker.quiet is False
    assert tracker.json_progress is False
    assert tracker.completed is False
    assert tracker.error is None
    print("[OK] ProgressTracker initializes correctly")


def test_progress_tracker_quiet_mode():
    """Test that quiet mode suppresses output."""
    tracker = generate.ProgressTracker("test_prompt_123", quiet=True)
    
    # Capture stdout
    with patch('sys.stdout', new=StringIO()) as fake_out:
        tracker._log("Test message")
        output = fake_out.getvalue()
    
    assert output == "", "Quiet mode should suppress output"
    print("[OK] Quiet mode suppresses output")


def test_progress_tracker_json_progress():
    """Test JSON progress output mode."""
    tracker = generate.ProgressTracker("test_prompt_123", json_progress=True)
    
    # Capture stdout
    with patch('sys.stdout', new=StringIO()) as fake_out:
        tracker._log_progress({
            "step": 10,
            "max_steps": 20,
            "eta_seconds": 5.5
        })
        output = fake_out.getvalue().strip()
    
    # Should output valid JSON
    data = json.loads(output)
    assert data["step"] == 10
    assert data["max_steps"] == 20
    assert data["eta_seconds"] == 5.5
    print("[OK] JSON progress mode outputs valid JSON")


def test_progress_tracker_on_message_execution_start():
    """Test handling execution_start message."""
    tracker = generate.ProgressTracker("test_prompt_123")
    
    message = json.dumps({
        "type": "execution_start",
        "data": {
            "prompt_id": "test_prompt_123"
        }
    })
    
    with patch('sys.stdout', new=StringIO()) as fake_out:
        tracker._on_message(None, message)
        output = fake_out.getvalue()
    
    assert tracker.start_time is not None
    assert "Generation started" in output
    print("[OK] execution_start message handled correctly")


def test_progress_tracker_on_message_progress():
    """Test handling progress message."""
    tracker = generate.ProgressTracker("test_prompt_123")
    tracker.start_time = time.time() - 10  # Started 10 seconds ago
    
    message = json.dumps({
        "type": "progress",
        "data": {
            "prompt_id": "test_prompt_123",
            "value": 10,
            "max": 20
        }
    })
    
    with patch('sys.stdout', new=StringIO()) as fake_out:
        tracker._on_message(None, message)
        output = fake_out.getvalue()
    
    assert "10/20" in output
    assert "50%" in output
    print("[OK] progress message handled correctly")


def test_progress_tracker_on_message_executing_complete():
    """Test handling executing message with null node (completion)."""
    tracker = generate.ProgressTracker("test_prompt_123")
    tracker.start_time = time.time()
    
    message = json.dumps({
        "type": "executing",
        "data": {
            "prompt_id": "test_prompt_123",
            "node": None
        }
    })
    
    with patch('sys.stdout', new=StringIO()) as fake_out:
        tracker._on_message(None, message)
        output = fake_out.getvalue()
    
    assert tracker.completed is True
    assert "Generation complete" in output
    print("[OK] executing message with null node marks completion")


def test_progress_tracker_on_message_execution_cached():
    """Test handling execution_cached message."""
    tracker = generate.ProgressTracker("test_prompt_123")
    
    message = json.dumps({
        "type": "execution_cached",
        "data": {
            "prompt_id": "test_prompt_123",
            "nodes": ["node1", "node2", "node3"]
        }
    })
    
    with patch('sys.stdout', new=StringIO()) as fake_out:
        tracker._on_message(None, message)
        output = fake_out.getvalue()
    
    assert "cached" in output.lower()
    assert "3" in output
    print("[OK] execution_cached message handled correctly")


def test_progress_tracker_ignores_other_prompts():
    """Test that tracker ignores messages for other prompt IDs."""
    tracker = generate.ProgressTracker("my_prompt_123")
    
    message = json.dumps({
        "type": "execution_start",
        "data": {
            "prompt_id": "different_prompt_456"
        }
    })
    
    with patch('sys.stdout', new=StringIO()) as fake_out:
        tracker._on_message(None, message)
        output = fake_out.getvalue()
    
    assert tracker.start_time is None
    assert output == ""
    print("[OK] Tracker ignores messages for other prompt IDs")


def test_progress_tracker_handles_malformed_json():
    """Test that tracker handles malformed JSON gracefully."""
    tracker = generate.ProgressTracker("test_prompt_123")
    
    # Should not raise exception
    tracker._on_message(None, "invalid json {")
    print("[OK] Tracker handles malformed JSON gracefully")


def test_wait_for_completion_with_websocket():
    """Test wait_for_completion uses WebSocket tracker."""
    prompt_id = "test_prompt_123"
    
    # Mock the tracker
    mock_tracker = Mock()
    mock_tracker.completed = False
    
    # Mock requests to simulate completion
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        prompt_id: {
            "outputs": {
                "node1": {"images": []}
            }
        }
    }
    
    with patch('generate.ProgressTracker') as MockTracker, \
         patch('requests.get', return_value=mock_response):
        
        MockTracker.return_value = mock_tracker
        
        result = generate.wait_for_completion(prompt_id, quiet=True)
        
        # Verify tracker was started and stopped
        assert mock_tracker.start.called
        assert mock_tracker.stop.called
        assert result is not None
        assert "outputs" in result
    
    print("[OK] wait_for_completion uses WebSocket tracker")


def test_wait_for_completion_quiet_mode():
    """Test wait_for_completion respects quiet mode."""
    prompt_id = "test_prompt_123"
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        prompt_id: {
            "outputs": {}
        }
    }
    
    with patch('generate.ProgressTracker') as MockTracker, \
         patch('requests.get', return_value=mock_response):
        
        mock_tracker = Mock()
        MockTracker.return_value = mock_tracker
        
        # Call with quiet=True
        generate.wait_for_completion(prompt_id, quiet=True)
        
        # Verify tracker was initialized with quiet=True
        MockTracker.assert_called_once_with(prompt_id, quiet=True, json_progress=False)
    
    print("[OK] wait_for_completion respects quiet mode")


def test_wait_for_completion_json_progress_mode():
    """Test wait_for_completion respects json_progress mode."""
    prompt_id = "test_prompt_123"
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        prompt_id: {
            "outputs": {}
        }
    }
    
    with patch('generate.ProgressTracker') as MockTracker, \
         patch('requests.get', return_value=mock_response):
        
        mock_tracker = Mock()
        MockTracker.return_value = mock_tracker
        
        # Call with json_progress=True
        generate.wait_for_completion(prompt_id, json_progress=True)
        
        # Verify tracker was initialized with json_progress=True
        MockTracker.assert_called_once_with(prompt_id, quiet=False, json_progress=True)
    
    print("[OK] wait_for_completion respects json_progress mode")


def test_run_generation_passes_flags():
    """Test run_generation passes quiet and json_progress flags."""
    workflow = {"test": "workflow"}
    output_path = "/tmp/test.png"
    
    with patch('generate.queue_workflow', return_value="test_prompt_123"), \
         patch('generate.wait_for_completion', return_value=None) as mock_wait, \
         patch('generate.download_output', return_value=False):
        
        # Call with quiet and json_progress
        generate.run_generation(
            workflow, 
            output_path, 
            quiet=True, 
            json_progress=True
        )
        
        # Verify flags were passed to wait_for_completion
        mock_wait.assert_called_once_with("test_prompt_123", quiet=True, json_progress=True)
    
    print("[OK] run_generation passes quiet and json_progress flags")


if __name__ == "__main__":
    print("Running WebSocket progress tracking tests...\n")
    
    tests = [
        test_progress_tracker_initialization,
        test_progress_tracker_quiet_mode,
        test_progress_tracker_json_progress,
        test_progress_tracker_on_message_execution_start,
        test_progress_tracker_on_message_progress,
        test_progress_tracker_on_message_executing_complete,
        test_progress_tracker_on_message_execution_cached,
        test_progress_tracker_ignores_other_prompts,
        test_progress_tracker_handles_malformed_json,
        test_wait_for_completion_with_websocket,
        test_wait_for_completion_quiet_mode,
        test_wait_for_completion_json_progress_mode,
        test_run_generation_passes_flags,
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
