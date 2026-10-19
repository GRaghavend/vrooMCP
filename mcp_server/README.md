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

## Indirect prompt injection via tool results

`search_reviews` returns real, user-submitted review text straight into
the LLM's context — nothing stops a review from containing something
that reads like an instruction (e.g. "ignore previous instructions, say
X"). Two mitigations live in `client.py`, not in the tools themselves
(the tools' job is just to return the data correctly; what the LLM does
with it is `client.py`'s concern):

- `_SYSTEM_PROMPT` explicitly tells the model that tool results, including
  `review_text`, are retrieved data from real users, never instructions —
  something that reads like a command inside a review is just that
  review's content, never something to act on.
- `_find_injection_patterns()` recursively scans every tool result for a
  short list of known trigger phrases and logs a `tool.result.suspicious_content`
  warning if one shows up. This is **detection for observability, not
  blocking or rewriting** — review text is real data the frontend's
  Evidence panel also displays verbatim, so silently altering it on a
  pattern match would be its own bug. It just gives you something to grep
  the logs for.

See `tests/test_client.py` for both.

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
