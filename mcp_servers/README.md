# MCP Servers

This directory contains specialized MCP (Model Context Protocol) servers for comfy-gen.

## Available Servers

### civitai_mcp.py

CivitAI Model Discovery Server - Provides tools for:
- Searching models on CivitAI
- Getting model details and metadata
- Hash-based model verification (CRITICAL for LoRA compatibility)
- Getting authenticated download URLs

**Usage:**
```bash
python3 mcp_servers/civitai_mcp.py
```

**Environment Variables:**
- `CIVITAI_API_KEY` (optional) - Enables NSFW content access and higher rate limits

**Exposed Tools:**
- `civitai_search_models(query, model_type, base_model, sort, nsfw, limit)`
- `civitai_get_model(model_id)`
- `civitai_lookup_hash(file_hash)` - **KEY FEATURE** for LoRA verification
- `civitai_get_download_url(model_id, version_id)`

## Configuration

MCP servers are configured in `../mcp_config.json`:

```json
{
  "mcpServers": {
    "civitai": {
      "command": ".venv/bin/python3",
      "args": ["mcp_servers/civitai_mcp.py"],
      "env": {
        "CIVITAI_API_KEY": "${CIVITAI_API_KEY}"
      }
    }
  }
}
```

## Testing

```bash
# Unit tests
python3 tests/test_civitai_mcp.py

# Integration tests (requires internet)
python3 tests/test_civitai_integration.py

# Examples
python3 examples/civitai_mcp_examples.py
```

## Documentation

See `../docs/MCP_SERVERS.md` for complete documentation of all MCP tools and usage examples.

## Adding New Servers

To add a new MCP server:

1. Create `new_server_mcp.py` in this directory
2. Follow the pattern from `civitai_mcp.py`:
   ```python
   from mcp.server import FastMCP
   
   mcp = FastMCP("Server Name")
   
   @mcp.tool()
   async def tool_name(param: str) -> dict:
       """Tool description."""
       return {"status": "success", "result": ...}
   
   if __name__ == "__main__":
       mcp.run()
   ```
3. Add configuration to `../mcp_config.json`
4. Create tests in `../tests/test_new_server_mcp.py`
5. Document in `../docs/MCP_SERVERS.md`
