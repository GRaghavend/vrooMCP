# backend

The HTTP layer between the frontend (`../frontend`, a React + TypeScript
+ Vite app running on a separate origin during local dev) and
`mcp_server/client.py`'s chat loop.

`mcp_server/client.py` provides the chat logic (`run_chat()`) but
deliberately no HTTP server, no process lifecycle, and no conversation
persistence — those are the caller's job. This is that caller: a FastAPI
app (`main.py`) that:

- starts one `MCPToolClient` when the API process starts and reuses it for
  every request (spawning the MCP server subprocess and loading ~32K CSV
  rows per request would be far too slow — see `mcp_server/client.py`'s
  own docstring on this),
- keeps an in-memory `conversation_id -> history` dict so multi-turn chats
  work across separate HTTP requests (`run_chat()` itself is stateless per
  call and expects the caller to replay history),
- exposes that as two routes over the existing `ChatRequest`/`ChatResponse`
  contract already defined in `mcp_server/models.py` (no parallel schema
  was introduced).

## Routes

- `POST /chat` — body: `ChatRequest {conversation_id?, message}`. Response:
  `ChatResponse {conversation_id, message_id, answer_text, tool_calls,
  status}`. Runs one turn of the chat loop; `status="error"` (LLM
  unreachable, or the tool-calling loop ran out of rounds) is still a
  normal `200` — same convention the tools themselves use for
  `brand_not_found`/`no_results` rather than raising. A genuine backend
  failure (MCP subprocess not connected, an unexpected exception) is a
  `503` instead, since there's no valid `answer_text` to return in that
  case.
- `GET /health` — `{status, mcp_connected, tool_count}`. Lets the frontend
  show a "connecting.../unavailable" state instead of discovering it only
  via a failed chat request.

## Known v1 shortcuts

- Conversation history lives in a plain in-memory `dict` on the API
  process — no TTL, no eviction, and it's gone on every restart. Fine for
  local dev with one process; would need a real store (Redis, a DB) before
  running more than one API worker or persisting across restarts.
- CORS origins are hardcoded to common local dev ports
  (`localhost:5173`/`localhost:3000`); tighten before any real deployment.

## Running

See [`../steps_to_run.md`](../steps_to_run.md) for the full sequence
including Ollama and the frontend dev server. Backend-only:

```bash
source .venv_mcp/bin/activate
pip install -r requirements.txt

# Requires Ollama running locally with the model pulled (see mcp_server/README.md)
uvicorn backend.main:app --reload
```

Run from the repo root so `backend/main.py`'s own `sys.path` setup can
find `mcp_server/` the same way `scripts/manual_test.py` does. On startup
it spawns `mcp_server/server.py` as a subprocess exactly once, the same
way `scripts/manual_test.py` does for a single manual run.
