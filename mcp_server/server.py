"""
Car Buying Advisor MCP Server.

Exposes 6 deterministic, unit-testable tools over precomputed analysis
tables (non-NLP EDA, sentiment classification, BERTopic topic modeling).
No tool calls an LLM; each is a plain Python function reading pre-built
CSVs already produced upstream (see the top-level README for the full
pipeline, and tools/ for one module per tool).

Run with:
    source .venv_mcp/bin/activate
    python mcp_server/server.py
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from tools import (
    compare_brands,
    get_brand_stats,
    get_common_complaints,
    get_common_praises,
    get_rating_trends,
    search_reviews,
)

server = MCPServer(name="car-buying-advisor")

# Registration is kept separate from each tool's definition (tools/*.py) so
# every tool stays a plain, independently importable/unit-testable function
# -- this is the only place that ties them to the running MCPServer instance.
for _tool_fn in (
    get_brand_stats,
    compare_brands,
    get_common_complaints,
    get_common_praises,
    get_rating_trends,
    search_reviews,
):
    server.tool()(_tool_fn)


if __name__ == "__main__":
    import asyncio

    asyncio.run(server.run_stdio_async())
