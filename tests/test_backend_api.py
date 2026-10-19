"""
Tests for backend/main.py -- the FastAPI layer in front of mcp_server.

What these tests do NOT do, on purpose:
  - start the real MCP subprocess
  - load the real CSV data
  - call the real Ollama model

Instead we replace (= "monkeypatch") the two things backend/main.py
depends on -- `mcp_client.MCPToolClient` and `mcp_client.run_chat` --
with small fakes we fully control. That's what makes this test file
fast (runs in well under a second) and deterministic (same result
every single run, on any machine, with no model installed).

Run with:
    pytest tests/test_backend_api.py -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import main as backend_main  # path to backend/ set up in tests/conftest.py


class FakeMCPToolClient:
    """Stands in for mcp_client.MCPToolClient. Same shape (start/stop/
    session/tool_schemas), zero subprocess, zero CSV, zero Ollama."""

    def __init__(self) -> None:
        self.session = None
        self.tool_schemas: list[dict] = []

    async def start(self) -> None:
        self.session = "fake-session"          # anything not-None
        self.tool_schemas = [{"type": "function", "function": {"name": "get_brand_stats"}}]

    async def stop(self) -> None:
        self.session = None


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Gives each test a fresh TestClient wired to a FakeMCPToolClient,
    and a fresh, isolated SQLite file for conversation history (store.py's
    DB_PATH is a module-level constant that would otherwise point every
    test at the same real backend/conversations.db and leak state between
    them). Also resets the rate limiter's counters -- main.py's `limiter`
    is a single module-level object shared by every test in this file, so
    without this a test late in the file could start seeing 429s from
    quota an earlier test already spent against the same (fake) client IP."""
    monkeypatch.setattr(backend_main.mcp_client, "MCPToolClient", FakeMCPToolClient)
    monkeypatch.setattr(backend_main.store, "DB_PATH", tmp_path / "test_conversations.db")
    backend_main.limiter.reset()

    # TestClient as a "with" block is what actually runs the app's
    # lifespan (the startup/shutdown code in backend/main.py) --
    # without the "with", startup never happens and app.state.mcp_client
    # would not exist yet.
    with TestClient(backend_main.app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_reports_connected(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mcp_connected"] is True
    assert body["tool_count"] == 1  # one fake tool schema, see FakeMCPToolClient.start


def test_health_reports_unavailable_when_mcp_not_connected(client):
    # Simulate the MCP subprocess having died / never connected.
    client.app.state.mcp_client.session = None

    response = client.get("/health")

    assert response.status_code == 200          # /health itself never errors
    assert response.json()["status"] == "unavailable"
    assert response.json()["mcp_connected"] is False


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

def test_chat_rejects_when_mcp_not_connected(client):
    client.app.state.mcp_client.session = None

    response = client.post("/chat", json={"message": "What's the best brand?"})

    assert response.status_code == 503


def test_chat_happy_path_returns_answer_and_generates_conversation_id(client, monkeypatch):
    fake_result = {"answer_text": "Toyota has the highest average rating.", "status": "ok", "tool_calls": []}
    monkeypatch.setattr(backend_main.mcp_client, "run_chat", AsyncMock(return_value=fake_result))

    response = client.post("/chat", json={"message": "Which brand rates highest?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer_text"] == "Toyota has the highest average rating."
    assert body["status"] == "ok"
    assert body["conversation_id"]  # a new id was generated, since we sent none
    assert body["message_id"]


def test_chat_reuses_the_conversation_id_it_was_given(client, monkeypatch):
    fake_result = {"answer_text": "Sure, here's more detail.", "status": "ok", "tool_calls": []}
    monkeypatch.setattr(backend_main.mcp_client, "run_chat", AsyncMock(return_value=fake_result))

    response = client.post("/chat", json={"conversation_id": "abc-123", "message": "Tell me more"})

    assert response.json()["conversation_id"] == "abc-123"


def test_chat_appends_user_and_assistant_turns_to_history(client, monkeypatch):
    """backend/main.py's docstring promises history grows by exactly one
    user message + one assistant message per turn -- this locks that in."""
    fake_result = {"answer_text": "BMW's main complaint is infotainment.", "status": "ok", "tool_calls": []}
    monkeypatch.setattr(backend_main.mcp_client, "run_chat", AsyncMock(return_value=fake_result))

    response = client.post("/chat", json={"conversation_id": "conv-1", "message": "What do BMW owners dislike?"})
    conversation_id = response.json()["conversation_id"]

    history = asyncio.run(backend_main.store.get_history(conversation_id))
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "What do BMW owners dislike?"}
    assert history[1] == {"role": "assistant", "content": "BMW's main complaint is infotainment."}


def test_history_survives_a_backend_restart(tmp_path, monkeypatch):
    """The whole point of moving off the old in-memory dict: conversation
    history must still be there after the process restarts, as long as
    it's pointed at the same database file. A second TestClient here
    (its own lifespan start/stop cycle) stands in for that restart."""
    monkeypatch.setattr(backend_main.mcp_client, "MCPToolClient", FakeMCPToolClient)
    monkeypatch.setattr(backend_main.store, "DB_PATH", tmp_path / "persist.db")
    fake_result = {"answer_text": "ok", "status": "ok", "tool_calls": []}
    monkeypatch.setattr(backend_main.mcp_client, "run_chat", AsyncMock(return_value=fake_result))

    with TestClient(backend_main.app) as first_run:
        response = first_run.post("/chat", json={"conversation_id": "conv-restart", "message": "How's the ride?"})
        assert response.status_code == 200

    with TestClient(backend_main.app) as second_run:
        response = second_run.post("/chat", json={"conversation_id": "conv-restart", "message": "And handling?"})
        assert response.status_code == 200

    history = asyncio.run(backend_main.store.get_history("conv-restart"))
    assert len(history) == 4  # 2 turns x (user + assistant), from both "processes" combined


def test_chat_returns_200_even_when_run_chat_reports_its_own_error_status(client, monkeypatch):
    """run_chat()'s status="error" (e.g. Ollama unreachable) is a normal,
    expected outcome the frontend already knows how to render -- it must
    NOT become an HTTP error response."""
    fake_result = {"answer_text": "I'm having trouble reaching the assistant model.", "status": "error", "tool_calls": []}
    monkeypatch.setattr(backend_main.mcp_client, "run_chat", AsyncMock(return_value=fake_result))

    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json()["status"] == "error"


def test_chat_returns_503_not_a_crash_when_run_chat_raises(client, monkeypatch):
    """If something inside run_chat throws an unexpected exception, the API
    must still return a clean 503 -- not a raw 500 with a stack trace
    leaked to the frontend."""
    monkeypatch.setattr(backend_main.mcp_client, "run_chat", AsyncMock(side_effect=RuntimeError("boom")))

    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert "boom" not in response.text  # internal exception detail must not leak to the client


def test_chat_rejects_empty_message(client):
    """ChatRequest.message has min_length=1 (mcp_server/models.py) --
    this is FastAPI's automatic request validation, not our own code,
    but it's part of the contract the frontend relies on, so we pin it."""
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Rate limiting (slowapi, keyed by client IP -- see main.py's `limiter`)
# ---------------------------------------------------------------------------

def test_chat_is_rate_limited_after_too_many_requests_in_a_minute(client, monkeypatch):
    """main.py caps /chat at 10/minute per IP. The 11th request in the same
    window must be rejected with 429 instead of reaching run_chat() at all."""
    fake_result = {"answer_text": "ok", "status": "ok", "tool_calls": []}
    monkeypatch.setattr(backend_main.mcp_client, "run_chat", AsyncMock(return_value=fake_result))

    for _ in range(10):
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 200

    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 429
