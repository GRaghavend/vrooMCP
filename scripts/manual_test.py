"""
Manual test script for the chat loop -- run this before wiring up the UI.
Not part of the shipped MCP server; kept in scripts/ as a throwaway
dev-only entry point (safe to delete once a real test suite / UI exists).

This spawns the real MCP server (mcp_server/server.py) as a subprocess,
talks to it over the actual Model Context Protocol (stdio transport), and
drives one chat turn through the local Ollama model.

Edit QUERY below and run `python scripts/manual_test.py` to see, in one
shot:
  1. The model's final answer.
  2. Every tool call it made (name, arguments, result status, duration).
  3. The client-side structured JSON log lines for this run (logs/app.log,
     tagged with a request_id).
  4. A reminder to check logs/mcp_server.log for the tool server's own
     side of the same calls -- a separate process, so its log lines
     aren't tagged with this request_id (see mcp_server/client.py docstring).

Usage:
    source .venv_mcp/bin/activate
    python scripts/manual_test.py
"""

import asyncio
import sys
import uuid
from pathlib import Path

MCP_SERVER_DIR = Path(__file__).resolve().parent.parent / "mcp_server"
sys.path.insert(0, str(MCP_SERVER_DIR))

import client as mcp_client  # noqa: E402  (path must be set up first)
from logging_config import request_id_var  # noqa: E402

# ---- Edit this to try different questions ---------------------------------
QUERY = "What are the top complaints about Audi's mileage?"

# Other things worth trying:
# QUERY = "Compare Audi and BMW overall."
# QUERY = "Compare Audi and BMW on mileage."          # compound: multiple tool calls expected
# QUERY = "What do people say about Toyota?"          # unknown brand -> brand_not_found
# QUERY = "Find reviews mentioning transmission problems in Audi."
# QUERY = "How has Lexus's rating changed between 2015 and 2018?"
# -----------------------------------------------------------------------------


async def main() -> None:
    request_id = str(uuid.uuid4())[:8]
    token = request_id_var.set(request_id)

    print(f"\n{'=' * 70}\nQUERY: {QUERY}\nrequest_id: {request_id}\n{'=' * 70}\n")

    async with mcp_client.MCPToolClient() as active_client:
        print(f"Connected to MCP server. {len(active_client.tool_schemas)} tools available: "
              f"{[s['function']['name'] for s in active_client.tool_schemas]}\n")
        result = await mcp_client.run_chat(QUERY, client=active_client)

    print("STATUS:", result["status"])
    print("\nANSWER:\n" + result["answer_text"])

    request_id_var.reset(token)


if __name__ == "__main__":
    asyncio.run(main())
