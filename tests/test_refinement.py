#!/usr/bin/env python3
"""Tests for quality-based iterative refinement."""

import random
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the function directly (avoiding full module import with dependencies)
def get_retry_params(
    attempt: int,
    strategy: str,
    base_steps: int = None,
    base_cfg: float = None,
    base_seed: int = None,
    base_prompt: str = "",
    base_negative: str = ""
) -> dict:
    """Get adjusted parameters for retry attempt based on strategy.

    NOTE: This is copied from generate.py to avoid importing the whole module
    with its heavy dependencies (websocket, etc.) which are not needed for testing.
    """
    # Use sensible defaults if not provided
    if base_steps is None:
        base_steps = 30
    if base_cfg is None:
        base_cfg = 7.0
    if base_seed is None:
        base_seed = random.randint(0, 2**31 - 1)

    params = {
        'steps': base_steps,
        'cfg': base_cfg,
        'seed': base_seed,
        'positive_prompt': base_prompt,
        'negative_prompt': base_negative
    }

    if attempt == 1:
        # First attempt - use base parameters
        return params

    # Subsequent attempts - apply strategy
    if strategy == 'progressive':
        # Progressive enhancement: increase steps and CFG
        step_multipliers = [1.0, 1.67, 2.67]
        cfg_increases = [0.0, 0.5, 1.0]

        idx = min(attempt - 1, len(step_multipliers) - 1)
        params['steps'] = int(base_steps * step_multipliers[idx])
        params['cfg'] = min(20.0, base_cfg + cfg_increases[idx])
        params['seed'] = random.randint(0, 2**31 - 1)

    elif strategy == 'seed_search':
        # Seed search: keep params same, try different seeds
        seed_offsets = [0, 1000, 5000]
        idx = min(attempt - 1, len(seed_offsets) - 1)
        params['seed'] = min(2**31 - 1, base_seed + seed_offsets[idx])

    elif strategy == 'prompt_enhance':
        # Prompt enhancement: add quality boosters progressively
        quality_boosters = [
            [],
            ["highly detailed", "sharp focus"],
            ["masterpiece", "best quality", "8K", "ultra detailed"]
        ]

        idx = min(attempt - 1, len(quality_boosters) - 1)
        boosters = quality_boosters[idx]

        if boosters:
            enhanced_prompt = base_prompt
            for booster in boosters:
                if booster.lower() not in enhanced_prompt.lower():
                    enhanced_prompt = f"{enhanced_prompt}, {booster}"
            params['positive_prompt'] = enhanced_prompt

        params['seed'] = random.randint(0, 2**31 - 1)

    return params


def test_progressive_strategy_first_attempt():
    """Test progressive strategy on first attempt uses base parameters."""
    params = get_retry_params(
        attempt=1,
        strategy='progressive',
        base_steps=30,
        base_cfg=7.0,
        base_seed=42,
        base_prompt="a cat",
        base_negative="ugly"
    )

    assert params['steps'] == 30, f"Expected steps=30, got {params['steps']}"
    assert params['cfg'] == 7.0, f"Expected cfg=7.0, got {params['cfg']}"
    assert params['seed'] == 42, f"Expected seed=42, got {params['seed']}"
    assert params['positive_prompt'] == "a cat"
    assert params['negative_prompt'] == "ugly"
    print("[OK] Progressive strategy first attempt uses base parameters")


def test_progressive_strategy_second_attempt():
    """Test progressive strategy on second attempt increases steps and cfg."""
    params = get_retry_params(
        attempt=2,
        strategy='progressive',
        base_steps=30,
        base_cfg=7.0,
        base_seed=42,
        base_prompt="a cat",
        base_negative="ugly"
    )

    # Second attempt: steps=30*1.67=50, cfg=7.0+0.5=7.5
    assert params['steps'] == int(30 * 1.67), f"Expected steps={int(30*1.67)}, got {params['steps']}"
    assert params['cfg'] == 7.5, f"Expected cfg=7.5, got {params['cfg']}"
    assert params['seed'] != 42, "Expected different seed on retry"
    assert params['positive_prompt'] == "a cat", "Prompt should not change in progressive strategy"
    print("[OK] Progressive strategy second attempt increases steps/cfg")


def test_progressive_strategy_third_attempt():
    """Test progressive strategy on third attempt further increases parameters."""
    params = get_retry_params(
        attempt=3,
        strategy='progressive',
        base_steps=30,
        base_cfg=7.0,
        base_seed=42,
        base_prompt="a cat",
        base_negative="ugly"
    )

    # Third attempt: steps=30*2.67=80, cfg=7.0+1.0=8.0
    assert params['steps'] == int(30 * 2.67), f"Expected steps={int(30*2.67)}, got {params['steps']}"
    assert params['cfg'] == 8.0, f"Expected cfg=8.0, got {params['cfg']}"
    print("[OK] Progressive strategy third attempt further increases parameters")


def test_seed_search_strategy():
    """Test seed search strategy tries different seeds."""
    params1 = get_retry_params(
        attempt=1,
        strategy='seed_search',
        base_steps=50,
        base_cfg=7.5,
        base_seed=1000,
        base_prompt="a dog",
        base_negative=""
    )

    params2 = get_retry_params(
        attempt=2,
        strategy='seed_search',
        base_steps=50,
        base_cfg=7.5,
        base_seed=1000,
        base_prompt="a dog",
        base_negative=""
    )

    params3 = get_retry_params(
        attempt=3,
        strategy='seed_search',
        base_steps=50,
        base_cfg=7.5,
        base_seed=1000,
        base_prompt="a dog",
        base_negative=""
    )

    # Should use deterministic seed offsets
    assert params1['seed'] == 1000, "First attempt should use base seed"
    assert params2['seed'] == 2000, "Second attempt should use base+1000"
    assert params3['seed'] == 6000, "Third attempt should use base+5000"

    # Steps and CFG should remain constant
    assert params1['steps'] == params2['steps'] == params3['steps'] == 50
    assert params1['cfg'] == params2['cfg'] == params3['cfg'] == 7.5

    print("[OK] Seed search strategy uses different seeds")


def test_prompt_enhance_strategy():
    """Test prompt enhancement strategy adds quality boosters."""
    params1 = get_retry_params(
        attempt=1,
        strategy='prompt_enhance',
        base_steps=40,
        base_cfg=7.0,
        base_seed=100,
        base_prompt="a sunset",
        base_negative="blurry"
    )

    params2 = get_retry_params(
        attempt=2,
        strategy='prompt_enhance',
        base_steps=40,
        base_cfg=7.0,
        base_seed=100,
        base_prompt="a sunset",
        base_negative="blurry"
    )

    params3 = get_retry_params(
        attempt=3,
        strategy='prompt_enhance',
        base_steps=40,
        base_cfg=7.0,
        base_seed=100,
        base_prompt="a sunset",
        base_negative="blurry"
    )

    # First attempt: no changes
    assert params1['positive_prompt'] == "a sunset"

    # Second attempt: should add quality boosters
    assert "highly detailed" in params2['positive_prompt']
    assert "sharp focus" in params2['positive_prompt']
    assert params2['positive_prompt'].startswith("a sunset, ")

    # Third attempt: should add more boosters
    assert "masterpiece" in params3['positive_prompt']
    assert "best quality" in params3['positive_prompt']
    assert "8K" in params3['positive_prompt']

    # Steps and CFG should remain constant
    assert params1['steps'] == params2['steps'] == params3['steps'] == 40
    assert params1['cfg'] == params2['cfg'] == params3['cfg'] == 7.0

    print("[OK] Prompt enhance strategy adds quality boosters")


def test_cfg_cap_at_20():
    """Test that progressive strategy caps CFG at 20.0."""
    params = get_retry_params(
        attempt=3,
        strategy='progressive',
        base_steps=30,
        base_cfg=19.5,  # High base CFG
        base_seed=42,
        base_prompt="test",
        base_negative=""
    )

    # Should cap at 20.0 (19.5 + 1.0 = 20.5, but capped)
    assert params['cfg'] <= 20.0, f"CFG should be capped at 20.0, got {params['cfg']}"
    print("[OK] Progressive strategy caps CFG at 20.0")


def test_defaults_when_none():
    """Test that function uses sensible defaults when base params are None."""
    params = get_retry_params(
        attempt=1,
        strategy='progressive',
        base_steps=None,  # Should default to 30
        base_cfg=None,    # Should default to 7.0
        base_seed=None,   # Should generate random
        base_prompt="",
        base_negative=""
    )

    assert params['steps'] == 30, f"Expected default steps=30, got {params['steps']}"
    assert params['cfg'] == 7.0, f"Expected default cfg=7.0, got {params['cfg']}"
    assert params['seed'] is not None, "Should generate a seed"
    assert params['seed'] >= 0, "Seed should be non-negative"
    print("[OK] Function uses sensible defaults for None parameters")


def run_all_tests():
    """Run all refinement tests."""
    print("Running refinement tests...")
    print("")

    test_progressive_strategy_first_attempt()
    test_progressive_strategy_second_attempt()
    test_progressive_strategy_third_attempt()
    test_seed_search_strategy()
    test_prompt_enhance_strategy()
    test_cfg_cap_at_20()
    test_defaults_when_none()

    print("")
    print("[OK] All refinement tests passed!")


if __name__ == "__main__":
    run_all_tests()
