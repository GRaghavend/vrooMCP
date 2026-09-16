"""
FastAPI backend for vrooMCP -- the HTTP layer in front of
mcp_server/client.py, for the frontend (a separate React app, different
origin during local dev) to talk to.

mcp_server/client.py deliberately provides no HTTP server, no client
lifecycle management, and no conversation persistence -- run_chat() is a
pure per-turn function; the caller is expected to hold a long-lived
MCPToolClient and replay history across turns. This module is that
caller: it owns the one long-lived MCPToolClient (started/stopped via the
app's lifespan, never per-request -- spawning the subprocess and loading
~32K CSV rows is too slow to repeat per chat message) and an in-memory
per-conversation history store.

Nothing in mcp_server/tools/ is touched or reimplemented here.
"""

from __future__ import annotations

import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
MCP_SERVER_DIR = REPO_ROOT / "mcp_server"
sys.path.insert(0, str(MCP_SERVER_DIR))

import client as mcp_client  # noqa: E402  (path must be set up first)
from logging_config import get_logger, log_event, request_id_var  # noqa: E402
from models import ChatRequest, ChatResponse  # noqa: E402

logger = get_logger("backend")

# conversation_id -> history, replayed into run_chat()'s `history` param on
# every turn. Plain in-memory dict: fine for a first version, but it grows
# forever (no TTL/eviction) and is wiped on every process restart -- a
# deliberate v1 shortcut, not an oversight.
#
# We store only {role, content} pairs for the user message and the final
# assistant answer of each turn -- not the intermediate tool-call/tool-result
# messages run_chat() builds internally for that turn's own reasoning, which
# it doesn't return to us anyway. This loses the model's exact intermediate
# steps from prior turns, but keeps the visible conversation (what the user
# asked, what they were told) intact for context on the next turn, which is
# what matters for a follow-up question like "what about BMW?".
_conversations: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp_client = mcp_client.MCPToolClient()
    await app.state.mcp_client.start()
    try:
        yield
    finally:
        await app.state.mcp_client.stop()


app = FastAPI(title="vrooMCP backend", lifespan=lifespan)

# Local dev only: the frontend (Vite/CRA dev server) runs on a different
# origin than this API. Tighten this list before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tag_request_id(request: Request, call_next):
    """Set the per-request id logging_config.py's contextvar expects, so
    every log line emitted while handling this request is tagged (see the
    module docstring: "set by FastAPI middleware, once that exists")."""
    token = request_id_var.set(str(uuid.uuid4())[:8])
    try:
        return await call_next(request)
    finally:
        request_id_var.reset(token)


@app.get("/health")
async def health(request: Request) -> dict:
    client: mcp_client.MCPToolClient = request.app.state.mcp_client
    connected = client.session is not None
    return {
        "status": "ok" if connected else "unavailable",
        "mcp_connected": connected,
        "tool_count": len(client.tool_schemas),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    client: mcp_client.MCPToolClient = request.app.state.mcp_client
    if client.session is None:
        raise HTTPException(status_code=503, detail="MCP tool server is not connected")

    conversation_id = req.conversation_id or str(uuid.uuid4())
    history = _conversations.setdefault(conversation_id, [])

    try:
        result = await mcp_client.run_chat(req.message, client=client, history=history)
    except Exception as exc:
        log_event(logger, 40, "chat.route.failed", error_type=type(exc).__name__, error=str(exc))
        raise HTTPException(status_code=503, detail="Chat backend is temporarily unavailable") from exc

    # run_chat()'s own status="error" paths (LLM unreachable, max tool
    # rounds exceeded) are expected outcomes, not system failures -- they
    # still get a normal 200 with status="error" in the body, same as the
    # brand_not_found/no_results convention the tools already use.
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": result["answer_text"]})

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=str(uuid.uuid4()),
        answer_text=result["answer_text"],
        tool_calls=result["tool_calls"],
        status=result["status"],
    )
