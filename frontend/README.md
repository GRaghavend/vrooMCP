# frontend

The chat + evidence-panel UI for vrooMCP — a two-pane layout: a chat
thread on the left, and an "Evidence" panel on the right that renders
whatever data the assistant's tool calls returned that turn (brand stat
tiles, complaint/praise bar charts, a rating-trend line chart, or a
review-search list), plus dedicated empty/error states for
`brand_not_found` / `topic_not_found` / `no_results`.

A real, runnable React + TypeScript + Vite app now lives in `src/`,
talking to the FastAPI backend (`../backend`) over `POST /chat` and
`GET /health`.

## What's here

- `design-export/vrooMCP.dc.html` — the finalized visual design, exported
  from Claude Design. **Reference only, not the app** — it's built in
  Claude Design's own template format (`<x-dc>`, `sc-if`, `sc-for`,
  `{{ }}` bindings) and every number/review/"tool call" in it is
  hardcoded JS (`STATS`, `NEGATIVE`, `POSITIVE`, `REVIEW_TEXT`, a
  synthetic `trendFor()` generator, a `route()` function that
  regex-matches the typed question). Kept for visual/interaction
  reference; not imported by the real app.
- `src/` — the real app:
  - `main.tsx`, `App.tsx` — entry point and top-level state (message
    list, conversation id, health status, which turn's evidence is
    pinned).
  - `api.ts` — the only file that talks to the backend: `checkHealth()`
    (`GET /health`) and `sendChatMessage()` (`POST /chat`).
  - `types.ts` — TypeScript types mirroring `mcp_server/models.py`
    field-for-field, so the two stay in sync deliberately, not by
    accident.
  - `evidence.ts` — turns one turn's raw `tool_calls` (as returned by
    `/chat`) into renderable evidence-panel sections. This is the piece
    that replaces the mock's `route()`/`computeEvidence()` — instead of
    guessing intent from regex, it reads whatever tools the LLM actually
    called (`get_brand_stats`, `compare_brands`, `get_common_complaints`,
    `get_common_praises`, `get_rating_trends`, `search_reviews`) and
    their real result shapes (including `brand_not_found` /
    `topic_not_found` / `no_results` statuses).
  - `components/ChatPane.tsx`, `components/EvidencePane.tsx` — the two
    panes.
  - `brandColors.ts` — a fixed color-per-brand mapping for the charts
    (UI convenience only, not a data source).
  - `styles.css` — global styles/design tokens ported from the `.dc.html`
    mock's inline `oklch(...)` colors and typography.

## What changed vs. the mock

- No hardcoded `STATS`/`NEGATIVE`/`POSITIVE`/`TRENDS`/`REVIEW_TEXT`, and
  no `route()` keyword-matcher — every number and piece of text on
  screen comes from a real `/chat` response.
- The mock's per-message follow-up "chips" were fabricated per turn by
  `route()`; the real backend doesn't return suggested follow-ups, so
  chips only appear on the initial greeting message as static starter
  prompts.
- The mock's `no_results` empty state offered a hardcoded list of
  alternative search terms; the real backend doesn't provide those, so
  that panel just surfaces the tool's own `message` field.
- Evidence sections are computed generically from whatever tools were
  called in a turn (not assumed to be exactly one "kind" per turn), so a
  turn that calls both `get_common_complaints` and `get_common_praises`
  (e.g. a brand-vs-brand aspect comparison, per the system prompt in
  `mcp_server/client.py`) renders both groups.

## Running

See the top-level `steps_to_run.md` for the full sequence (backend +
Ollama + this app). Short version, from this directory:

```bash
npm install       # first time only, or after package.json changes
npm run dev        # starts the Vite dev server on http://localhost:5173
```

Requires the backend running on `http://localhost:8000` (see
`../backend/README.md`) — CORS there is already opened for
`localhost:5173`. Override the backend URL with a `.env.local` file
containing `VITE_API_BASE_URL=http://localhost:8000` if needed.

Other scripts:

```bash
npm run typecheck   # tsc --noEmit -- type errors only, no build output
npm run lint         # eslint . -- code-quality checks (unused vars, hook misuse, etc.)
npm run build        # tsc -b && vite build -- production bundle (not run as part of this task)
npm run preview      # serve the production build locally, after `build`
```
