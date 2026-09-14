# frontend

The chat + evidence-panel UI for vrooMCP — a two-pane layout: a chat
thread on the left, and an "Evidence" panel on the right that renders
whatever data the assistant's tool calls returned that turn (brand stat
tiles, complaint/praise bar charts, a rating-trend line chart, or a
review-search list), plus dedicated empty/error states for
`brand_not_found` / `topic_not_found` / `no_results`.

## What's here right now

`design-export/vrooMCP.dc.html` — the finalized visual design, exported
from Claude Design. **This is a reference, not the app.** It's built in
Claude Design's own template format (`<x-dc>`, `sc-if`, `sc-for`,
`{{ }}` bindings, a `DCLogic` base class loaded from `support.js`) — that
only runs inside Claude Design's canvas, not in a browser or a normal
web build. It also has **zero real data**: every number, review, and
"tool call" in it is hardcoded JS at the top of the file (`STATS`,
`NEGATIVE`, `POSITIVE`, `REVIEW_TEXT`, a synthetic `trendFor()`
generator), and the chat behavior is faked by a `route()` function that
regex-matches keywords in the typed question instead of actually calling
an LLM or the MCP server.

## What's not here yet

A real, runnable frontend app. Building it means:

1. **Porting** the layout/styling/interaction design out of the
   `.dc.html` template syntax into a real framework (React, most likely,
   given the component already thinks in React terms — state, refs,
   `setState`) that can be built and served normally.
2. **Replacing the mock data layer** (`STATS`/`NEGATIVE`/`POSITIVE`/
   `TRENDS`/`REVIEW_TEXT`/`route()`) with real calls to a backend API —
   see the top-level README for how that conversation works once the
   FastAPI layer in front of `mcp_server/client.py` exists.

The design itself (chart choices, empty states, layout) was validated
against the real tool schemas in `mcp_server/models.py` before export —
see the design-tool prompt used to generate it, further back in this
project's history — so the data shapes it expects already line up with
what the real tools return; it's the wiring that's missing, not the
design.
