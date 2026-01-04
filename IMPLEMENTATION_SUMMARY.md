# Multi-dimensional Quality Scoring Implementation

This PR implements comprehensive image quality assessment using pyiqa, as specified in issue #70.

## What Was Implemented

### 1. Core Quality Module (`comfy_gen/quality.py`)

- **QualityScorer class** with four quality dimensions:
  - Technical quality (BRISQUE, NIQE) - measures artifacts, noise, blur
  - Aesthetic quality (LAION Aesthetic) - measures visual appeal
  - Detail quality (TOPIQ) - measures fine detail preservation
  - Prompt adherence (CLIP) - measures semantic match to prompt

- **Composite scoring** with weighted formula:
  - Technical: 30%
  - Aesthetic: 25%
  - Prompt Adherence: 25%
  - Detail: 20%

- **Letter grades** (A-F) based on composite score:
  - A (8.0-10.0): Production ready
  - B (6.5-7.9): Good, minor issues
  - C (5.0-6.4): Acceptable
  - D (3.0-4.9): Poor
  - F (0.0-2.9): Failed

### 2. CLI Tool

```bash
# Score existing image
python3 -m comfy_gen.quality /path/to/image.png

# Score with prompt for adherence checking
python3 -m comfy_gen.quality /path/to/image.png "a beautiful sunset"
```

### 3. Generate.py Integration

- New `--quality-score` flag to run quality assessment after generation
- Quality results automatically included in metadata JSON
- Scores displayed in CLI output

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a majestic lion" \
    --quality-score \
    --output /tmp/lion.png
```

### 4. Metadata Schema Updates

Quality scores are now stored in metadata:

```json
{
  "quality": {
    "composite_score": 7.8,
    "grade": "B",
    "technical": {
      "brisque": 7.2,
      "niqe": 6.8,
      "raw_brisque": 28.0,
      "raw_niqe": 32.0
    },
    "aesthetic": 8.1,
    "detail": 7.8,
    "prompt_adherence": {
      "clip": 8.5
    }
  }
}
```

### 5. Gallery Server Updates

- Quality grades displayed as color-coded badges
- Grades shown with tooltip containing composite score
- CSS styling for all grade levels (A-F)

### 6. Testing

- `tests/test_quality.py` - Unit tests for quality module
- `tests/test_quality_integration.py` - Integration tests
- All tests pass with and without pyiqa installed
- Backward compatibility verified

## Files Modified

1. `requirements.txt` - Added pyiqa dependency
2. `comfy_gen/quality.py` - New quality scoring module (429 lines)
3. `comfy_gen/__init__.py` - Export quality module
4. `comfy_gen/__main__.py` - CLI entry point
5. `generate.py` - Integrated quality scoring with --quality-score flag
6. `scripts/gallery_server.py` - Display quality grades
7. `docs/USAGE.md` - Added quality scoring documentation
8. `tests/test_quality.py` - Unit tests
9. `tests/test_quality_integration.py` - Integration tests

## Dependencies

```bash
pip install pyiqa
```

Note: The system gracefully handles missing pyiqa - all other functionality works without it.

## How to Use

### Basic Generation with Quality Scoring

```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --quality-score \
    --output /tmp/sunset.png
```

### Score Existing Images

```bash
python3 -m comfy_gen.quality /tmp/image.png "original prompt"
```

### View Quality Grades in Gallery

```bash
python3 scripts/gallery_server.py
# Open http://localhost:8080
```

## Test Results

All tests pass:
- `test_quality.py`: 6/6 passed
- `test_quality_integration.py`: 4/4 passed
- `test_validation.py`: 4/4 passed (no regression)
- `test_metadata_backward_compat.py`: Passed (backward compatible)

## Documentation

See `docs/USAGE.md` for complete usage guide with examples.

## Acceptance Criteria ✓

- [x] Install `pyiqa` and add to requirements.txt
- [x] Create `comfy_gen/quality.py` with `QualityScorer` class
- [x] Implement `score_image()` returning multi-dimensional scores
- [x] Add `--quality-score` flag to generate.py
- [x] Update metadata JSON schema with quality breakdown
- [x] Update `scripts/gallery_server.py` to display quality grades
- [x] CLI tool: `python3 -m comfy_gen.quality <image> [prompt]`

All acceptance criteria met!
