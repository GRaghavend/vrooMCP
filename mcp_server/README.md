# mcp_server

The serving layer: an MCP server exposing 6 deterministic tools over the
tables produced by `eda/`, `sentiment_classification/`, and
`topic_modelling/` (see the [top-level README](../README.md) for the full
pipeline and the tool → data file map), plus the Ollama chat client that
drives it.

## Layout

- `server.py` — the MCP server entry point. Registers each tool function
  from `tools/` against the `MCPServer` instance; run this as a subprocess
  (see `client.py`), never imported for its data.
- `tools/` — one file per tool, each a plain, independently importable
  function (not tied to the server instance):
  - `brand_stats.py` → `get_brand_stats`
  - `compare_brands.py` → `compare_brands` (composes `get_brand_stats`)
  - `common_complaints.py` → `get_common_complaints`
  - `common_praises.py` → `get_common_praises`
  - `rating_trends.py` → `get_rating_trends`
  - `search_reviews.py` → `search_reviews`
  - `topic_query.py` — shared query logic behind the complaints/praises
    tools (not a tool itself)
  - `shared.py` — the data layer: loads all 5 CSVs from `data/processed/`
    once at import time, plus brand/topic resolution helpers and the
    `logged_tool` decorator every tool is wrapped with
- `models.py` — Pydantic output schemas for every tool, plus the chat
  contract (`ChatRequest`/`ChatResponse`/`ToolCallLog`) for the FastAPI
  layer ahead.
- `client.py` — the MCP *client*: spawns `server.py` as a subprocess,
  drives the Ollama tool-calling loop (`MCPToolClient`, `run_chat`).
- `logging_config.py` — structured JSON logging shared by both processes
  (writes to `../logs/`, one file per process — see the module docstring).

Adding a 7th tool means adding one file to `tools/`, exporting it from
`tools/__init__.py`, and adding it to the registration loop in `server.py`
— nothing else changes.

## Running

There's no standalone entry point to run from this folder directly —
`server.py` is meant to be spawned as a subprocess by an MCP client, not
run on its own. Use `scripts/manual_test.py` at the repo root, which spawns
`server.py` for you and drives one chat turn end-to-end:

```bash
source .venv_mcp/bin/activate
python scripts/manual_test.py
```

See the top-level README for the full setup sequence and the tool → data
file map.
