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
- persists `conversation_id -> history` in a small SQLite database
  (`store.py`, `backend/conversations.db`, git-ignored) so multi-turn
  chats work across separate HTTP requests *and* survive a restart
  (`run_chat()` itself is stateless per call and expects the caller to
  replay history),
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
  case. Rate-limited to 10 requests/minute per client IP (`slowapi`) — a
  `429` if exceeded. Keyed by IP rather than a user id since there's no
  auth yet.
- `GET /health` — `{status, mcp_connected, tool_count}`. Lets the frontend
  show a "connecting.../unavailable" state instead of discovering it only
  via a failed chat request.

## Known v1 shortcuts

- Conversation history has no TTL/eviction — `backend/conversations.db`
  grows forever, there's just no risk of losing it on restart anymore.
  SQLite is also single-writer: fine for one API process (today's setup),
  but would need a real client-server DB (Postgres) before running more
  than one API worker against the same history.
- CORS origins are hardcoded to common local dev ports
  (`localhost:5173`/`localhost:3000`); tighten before any real deployment.
- The rate limit above is a flat per-IP cap, not per-user (no auth exists
  yet to key on), and resets on restart along with everything else
  in-memory.

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

### Running with Docker

An alternative to the manual venv setup above. Build context is the repo
root (the `Dockerfile` lives there, not in `backend/`), since the image
needs `mcp_server/` and `data/processed/` alongside `backend/`:

```bash
# Requires Ollama running on the host first:
#   ollama serve

docker compose up --build
```

This brings up both the backend (port 8000) and frontend (port 5173)
containers — Ollama itself is still not containerized (see the
`Dockerfile`'s comment for why). The compose file points the backend
container at the host's Ollama via `OLLAMA_HOST`. See
`frontend/Dockerfile`'s comment for how the frontend container reaches
the backend (short version: it doesn't need to — your browser does).
