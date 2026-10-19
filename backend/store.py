"""
SQLite-backed conversation history store.

Replaces the plain in-memory dict backend/main.py used to hold here
previously (a documented v1 shortcut): that dict was wiped on every
process restart and grew without bound for the life of the process.
This persists the same {role, content} pairs to a file on disk instead --
nothing about the ChatRequest/ChatResponse contract, run_chat(), or the
MCP side changes; only what backs `history` in main.py does.

One connection per call rather than one held open for the process's
lifetime -- SQLite handles many short-lived connections to the same file
fine, and this avoids any cross-request/cross-await sharing concerns a
single long-lived connection object would raise. sqlite3 itself is a
blocking API, so every call here runs in a thread (asyncio.to_thread)
rather than blocking the event loop -- the same pattern client.py already
uses for the blocking `ollama.chat` call.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "conversations.db"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)"
        )


async def init_db() -> None:
    """Create the table/index if they don't exist yet. Call once at
    process startup (see main.py's lifespan) -- cheap and idempotent, so
    safe to call every time the process starts even if the file already
    has the schema from a previous run."""
    await asyncio.to_thread(_init_db_sync)


def _get_history_sync(conversation_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]


async def get_history(conversation_id: str) -> list[dict]:
    """All turns stored so far for this conversation, oldest first. Empty
    list for an unseen conversation_id -- same shape the old dict's
    `.setdefault(conversation_id, [])` returned."""
    return await asyncio.to_thread(_get_history_sync, conversation_id)


def _append_turn_sync(conversation_id: str, user_message: str, assistant_message: str) -> None:
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            [
                (conversation_id, "user", user_message),
                (conversation_id, "assistant", assistant_message),
            ],
        )


async def append_turn(conversation_id: str, user_message: str, assistant_message: str) -> None:
    """Persist one turn: the user's message and the assistant's final
    answer for it -- the same two {role, content} entries per turn the
    old in-memory version appended, just written to disk now."""
    await asyncio.to_thread(_append_turn_sync, conversation_id, user_message, assistant_message)
