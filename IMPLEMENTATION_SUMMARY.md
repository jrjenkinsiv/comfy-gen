# Metadata Schema Enhancement - Summary

## Task Completed

Enhanced the metadata JSON schema to capture complete generation information for experiment reproducibility and quality tracking as specified in issue #XX.

## Changes Made

### 1. Core Functionality (generate.py)

#### New Helper Functions
- `extract_model_from_workflow()` - Automatically extracts base model from CheckpointLoader/UNETLoader
- `extract_vae_from_workflow()` - Extracts VAE model from VAELoader node
- `extract_resolution_from_workflow()` - Extracts [width, height] from EmptyLatentImage node

#### Updated `create_metadata_json()` Function
- Added `generation_id` parameter (UUID) for unique tracking
- Added `workflow` parameter for auto-extraction of model/VAE/resolution
- Added `output_path` parameter for file size calculation
- Added `generation_time_seconds` parameter for timing tracking
- Restructured return format from flat to nested schema

#### Updated `run_generation()` Function
- Added timing tracking (start to completion)
- Returns 4-tuple: (success, minio_url, object_name, generation_time_seconds)

#### Updated `main()` Function
- Passes workflow, output_path, and generation_time to create_metadata_json()
- Handles new 4-tuple return from run_generation()
- Maintains all existing functionality while using new schema

### 2. Gallery Server (scripts/gallery_server.py)

#### Backward Compatibility
- Updated JavaScript parsing to detect old vs new format
- Handles both flat and nested metadata structures
- Extracts additional fields (model, resolution, generation_time, file_size) when available
- Falls back gracefully to old format parsing

### 3. Tests

#### Updated Existing Tests (tests/test_metadata.py)
- `test_create_metadata_json()` - Updated for nested schema validation
- `test_create_metadata_json_minimal()` - Updated for nested structure
- Added `test_extract_model_from_workflow()` - Tests model extraction
- Added `test_extract_vae_from_workflow()` - Tests VAE extraction
- Added `test_extract_resolution_from_workflow()` - Tests resolution extraction

#### New Test Files
- `tests/test_metadata_schema_example.py` - Full demonstration of new schema
- `tests/test_metadata_backward_compat.py` - Verifies gallery compatibility

### 4. Documentation

#### Created docs/METADATA_SCHEMA.md
- Schema comparison (old vs new)
- Feature documentation
- Usage examples
- Implementation details
- Benefits overview

## New Schema Structure

```
{
  "timestamp": ISO datetime,
  "generation_id": UUID,
  
  "input": {
    "prompt": str,
    "negative_prompt": str,
    "preset": str|null
  },
  
  "workflow": {
    "name": str,
    "model": str|null (auto-extracted),
    "vae": str|null (auto-extracted)
  },
  
  "parameters": {
    "seed": int,
    "steps": int,
    "cfg": float,
    "sampler": str,
    "scheduler": str,
    "resolution": [width, height]|null (auto-extracted),
    "loras": [{"name": str, "strength": float}]
  },
  
  "quality": {
    "composite_score": null (placeholder for #70),
    "grade": null (placeholder for #70),
    "technical": null (placeholder for #70),
    "aesthetic": null (placeholder for #70),
    "prompt_adherence": {"clip": float|null},
    "detail": null (placeholder for #70)
  },
  
  "refinement": {
    "attempt": null (placeholder for #71),
    "max_attempts": null (placeholder for #71),
    "strategy": null (placeholder for #71),
    "previous_scores": null (placeholder for #71)
  },
  
  "storage": {
    "minio_url": str,
    "file_size_bytes": int|null (calculated),
    "format": str|null (calculated),
    "generation_time_seconds": float|null (tracked)
  }
}
```

## Acceptance Criteria Status

- ✅ Update `create_metadata_json()` in generate.py
- ✅ Add generation_id (UUID)
- ✅ Extract model/VAE from workflow
- ✅ Add resolution
- ✅ Add generation timing
- ✅ Add file size
- ✅ Restructure schema (nested input, workflow, parameters, storage)
- ✅ Maintain backward compatibility with existing metadata files
- ✅ Update `scripts/gallery_server.py` (parse new schema)
- ✅ Added quality and refinement placeholder sections for future features

## Test Results

All tests passing:
```
[OK] extract_workflow_params extracts KSampler parameters correctly
[OK] extract_workflow_params handles missing KSampler
[OK] extract_loras_from_workflow extracts LoRA information
[OK] extract_loras_from_workflow handles workflows without LoRAs
[OK] extract_model_from_workflow extracts model names correctly
[OK] extract_vae_from_workflow extracts VAE names correctly
[OK] extract_resolution_from_workflow extracts resolution correctly
[OK] create_metadata_json creates complete nested metadata structure
[OK] create_metadata_json handles minimal parameters with nested structure
[OK] upload_metadata_to_minio uploads JSON with correct parameters
[OK] All metadata tests passed!
```

## Files Modified

1. `generate.py` - Core metadata and generation functions
2. `scripts/gallery_server.py` - Backward compatible parsing
3. `tests/test_metadata.py` - Updated existing tests

## Files Created

1. `docs/METADATA_SCHEMA.md` - Comprehensive documentation
2. `tests/test_metadata_schema_example.py` - Full schema demonstration
3. `tests/test_metadata_backward_compat.py` - Compatibility tests

## Backward Compatibility

✅ Gallery server handles both old flat and new nested formats
✅ Existing metadata files continue to work
✅ No breaking changes to existing functionality

## Future Integration Points

The schema includes placeholder sections for:
- Issue #70: Quality scoring (composite_score, grade, technical, aesthetic, detail)
- Issue #71: Refinement tracking (attempt, max_attempts, strategy, previous_scores)

These sections are structured but null-valued, ready for future implementation.

## Benefits

1. **Complete Reproducibility** - All parameters captured for exact recreation
2. **Experiment Tracking** - Structured quality and refinement data
3. **Resource Monitoring** - File sizes and generation times for planning
4. **Extensible** - Ready for quality scoring and refinement features
5. **Backward Compatible** - Works with existing metadata files
