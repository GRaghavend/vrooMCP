# Car Buying Advisor — MCP Server + Ollama Chat Loop

A decision-support tool for choosing between luxury car brands from real
owner reviews: an MCP server exposing 6 deterministic, unit-testable tools
over precomputed analysis tables, plus a chat loop that drives a local
Ollama LLM (`qwen2.5:7b-instruct`) as a **real MCP client** of that server.

No tool calls an LLM internally — each is a plain Python function reading
a pre-built CSV. The LLM synthesizes answers from tool results;
comparison-by-aspect ("compare Audi and BMW on mileage") is achieved by the
LLM **composing multiple tool calls**, not by a dedicated tool — see
"Design notes" below.

**Status**: the MCP server and the Ollama chat loop are both working
end-to-end (see `scripts/manual_test.py`). The one piece not yet built is
a UI on top of the chat loop — everything below runs from the command line
until that exists.

## Repository layout

The repo is organized to mirror the order the project was actually built
in — raw data in, tables out, tools on top of the tables, chat loop on top
of the tools:

```
eda/                      1. Exploratory analysis on the raw reviews
sentiment_classification/ 2. Picks and applies a sentiment model
topic_modelling/          3. BERTopic topic modeling + aspect table
data/
  raw/                       Original review CSVs (input to step 1)
  interim/                   Intermediate pipeline artifacts
  processed/                 Final tables the MCP server reads
mcp_server/                4. The MCP server, its tools, and the Ollama client
scripts/                   Throwaway manual-run scripts (not shipped code)
logs/                       Structured JSON logs (git-ignored, created at runtime)
```

Each stage's own README (where one exists) has the detail; this file is
the map between them plus how to run everything.

## 1. EDA — `eda/`

Three notebooks establish dataset shape and quality, and produce the first
tables the MCP server reads directly (`brand_stats.csv`, `rating_trends.csv`,
`cleaned_reviews.csv`). Run in the order listed in
[`eda/README.md`](eda/README.md) — that file also has the full
data-quality findings and how they informed later steps.

## 2. Sentiment classification — `sentiment_classification/`

`sentimentclassification.ipynb` evaluates candidate sentiment models
(compared against the gold-labeled 3,700-review set validated in step 1)
and applies the winning model to the full 38K reviews. This notebook was
run on Kaggle (paths under `/kaggle/input/...` and `/kaggle/working/...`
are that platform's, left as-is — its local-relative outputs, e.g.
`phase4_model_comparison.csv`, are written under `data/interim/`). Its
sentiment predictions feed directly into topic modelling below.

## 3. Topic modelling — `topic_modelling/`

`topicmodelling.ipynb` (also run on Kaggle) runs BERTopic over the review
text and joins the result with the sentiment predictions from step 2,
producing `aspect_sentiment_table.csv` — one row per review with its
topic, keywords, and sentiment. Downloaded from Kaggle's working
directory into `data/processed/`.

`build_topic_info.py` is a small local, deterministic script that derives
`data/processed/phase5_topic_info.csv` (one row per topic: id, label,
keywords, review count) from `aspect_sentiment_table.csv`. It's the only
step in the pipeline that runs locally rather than on Kaggle:

```bash
python3 -m venv .venv_mcp
source .venv_mcp/bin/activate
pip install -r requirements.txt

python topic_modelling/build_topic_info.py
```

After this step, all 5 tables the MCP server needs exist in
`data/processed/`:

| File | Produced by |
|---|---|
| `brand_stats.csv` | `eda/EDA.ipynb` |
| `rating_trends.csv` | `eda/EDA.ipynb` |
| `cleaned_reviews.csv` | `eda/EDA_NPL_38K.ipynb` |
| `aspect_sentiment_table.csv` | `topic_modelling/topicmodelling.ipynb` (Kaggle) |
| `phase5_topic_info.csv` | `topic_modelling/build_topic_info.py` |

## 4. MCP server + chat loop — `mcp_server/`

`mcp_server/server.py` and `mcp_server/client.py` run as **two separate OS
processes**, talking over the actual Model Context Protocol (stdio
transport, JSON-RPC) — not a plain in-process function call:

```
Ollama (qwen2.5:7b-instruct)
        │  tool schemas ← fetched live from the MCP server's list_tools()
        │  tool_calls (name + args)
        ▼
mcp_server/client.py  (MCP client, process A)
        │  MCP call_tool() over stdio (JSON-RPC)
        ▼
mcp_server/server.py  (MCP server, process B — spawned as a subprocess)
        │  validates arguments itself (from the same schema it published)
        ▼
pandas DataFrames (5 CSVs from data/processed/, loaded once at server startup)
```

The tool JSON schemas handed to Ollama are **not** hand-maintained — they
come straight from the live server's `list_tools()` response, generated
from each tool function's own type-hinted signature (see
`mcp_server/tools/`, one file per tool). The server is the single source
of truth for what it can do; nothing in `client.py` duplicates that. See
[`mcp_server/README.md`](mcp_server/README.md) for the file-by-file
breakdown of that folder.

**Logging across the process boundary:** each process logs to its own file
(`logs/app.log` for the client/orchestrator, `logs/mcp_server.log` for the
tool server) — two independent `RotatingFileHandler`s rotating the *same*
file from separate processes can race and corrupt it. A `request_id` set in
`client.py` does **not** automatically appear in the server's log lines —
`contextvars` don't cross an OS process boundary. Today, matching a chat
turn's server-side tool logs to its client-side request_id means lining up
timestamps between the two files (`scripts/manual_test.py` prints a
reminder of this). The correct fix is to thread `request_id` through MCP's
per-call `meta` field and have server-side tools accept an injected
`Context` parameter to log through the protocol itself — a real upgrade,
deliberately deferred rather than done as a rushed addition to
already-tested tool code.

### Setup and running

```bash
python3 -m venv .venv_mcp
source .venv_mcp/bin/activate
pip install -r requirements.txt

# One-time (step 3 above, repeated here for convenience):
python topic_modelling/build_topic_info.py

# Requires Ollama running locally with the model pulled:
#   ollama pull qwen2.5:7b-instruct
python scripts/manual_test.py
```

`scripts/manual_test.py` spawns `mcp_server/server.py` as a subprocess
itself — you do not run `server.py` separately. All data is loaded into
memory once, at the server subprocess's startup. If a required file is
missing or a required column isn't present, that subprocess exits
immediately with a fatal error instead of starting silently broken
(visible in `logs/mcp_server.log` and in the client's stderr).

Edit the `QUERY` constant at the top of `scripts/manual_test.py` to try
different questions (single-tool, compound/multi-tool, unknown-brand). It
prints the model's answer, every tool call made (name, args, status,
duration), and the client-side structured log lines for that exact run.

## Tool → data file map

| Tool | Reads | Purpose |
|---|---|---|
| `get_brand_stats(brand_name)` | `data/processed/brand_stats.csv` | Avg/median rating, review count, rating std, avg model year for one brand |
| `compare_brands(brand_names)` | `data/processed/brand_stats.csv` | Same stats for N brands, side by side (calls `get_brand_stats` per brand) |
| `get_common_complaints(brand_name, topic_filter=None, top_n=5)` | `data/processed/aspect_sentiment_table.csv`, `data/processed/phase5_topic_info.csv` | Top negative-sentiment topics for a brand, optionally narrowed to one aspect |
| `get_common_praises(brand_name, topic_filter=None, top_n=5)` | `data/processed/aspect_sentiment_table.csv`, `data/processed/phase5_topic_info.csv` | Same, for positive-sentiment topics |
| `get_rating_trends(brand_name=None, year_range=None)` | `data/processed/rating_trends.csv` | Avg rating per model year, optionally filtered by brand and/or year range |
| `search_reviews(query, brand_name=None, min_rating=None, limit=20)` | `data/processed/cleaned_reviews.csv` | Case-insensitive substring search over raw review text |

`data/processed/phase5_topic_info.csv` is a reference table (topic_id,
topic_label, top_keywords, review_count) derived from
`aspect_sentiment_table.csv` by `topic_modelling/build_topic_info.py`. It
isn't a primary source for any tool — it's used to validate/fuzzy-match a
caller's `topic_filter` string against the 40 real BERTopic labels, and to
tell the caller which topics *do* exist when their filter doesn't match
anything.

## Data coverage

`brand_stats.csv`, `rating_trends.csv`, `cleaned_reviews.csv`, and
`aspect_sentiment_table.csv` all cover the same 5 brands: **Audi, BMW,
INFINITI, Lexus, Mercedes-Benz** (31,938 reviews total). Brand name matching
is case-insensitive; an unrecognized brand always returns an explicit
`brand_not_found` status plus the list of brands that *do* exist — never an
empty list or a crash.

## `topic_filter` matching

`get_common_complaints` / `get_common_praises` resolve `topic_filter` in two
passes:
1. **Substring match** against `topic_label` and `top_keywords` (case-insensitive)
   — e.g. `"mileage"` matches the topic labeled *"high mileage & maintenance
   reliability"*.
2. **Fuzzy match** (`difflib.get_close_matches`, cutoff 0.4) against known
   `topic_label` values, for near-miss spellings, if the substring pass finds
   nothing.

If neither pass matches, the tool returns `status="topic_not_found"` plus
`available_topics` (all 40 known labels) instead of silently returning `[]`.

## Error handling contract

Every tool returns a Pydantic model with a `status` field — never a bare
`None`, an empty list with no explanation, or an unhandled exception:

- Unknown brand → `status="brand_not_found"`, plus `available_brands`.
- Unknown/unmatched topic → `status="topic_not_found"`, plus `available_topics`.
- Valid brand/topic but zero matching rows → `status="no_results"`, plus a
  human-readable `message` explaining why.
- Otherwise → `status="ok"` with the populated result.

## Design notes: why there's no "compare by aspect" tool

A query like *"Compare Audi and BMW on mileage"* is **not** a single tool
call. There is no `compare_brands_by_topic` tool because it would just
re-implement calling `get_common_praises` / `get_common_complaints` twice
each (once per brand) and returning the same data those tools already
return. Instead, the LLM composes:

```
get_common_praises("Audi", topic_filter="mileage")
get_common_complaints("Audi", topic_filter="mileage")
get_common_praises("BMW", topic_filter="mileage")
get_common_complaints("BMW", topic_filter="mileage")
```

and synthesizes the comparison itself from the four results. Adding a
dedicated 7th tool would duplicate logic that composition of the existing 6
tools already covers — the tools are kept single-purpose and composable by
design.

## Testing without an LLM

Every tool is still a plain importable function (no subprocess needed), so
it's unit-testable directly by importing the tool modules in-process:

```python
import sys
sys.path.insert(0, "mcp_server")

from tools import get_brand_stats, compare_brands, get_common_complaints, get_common_praises, get_rating_trends, search_reviews

get_brand_stats("bmw")                                   # case-insensitive
get_brand_stats("Toyota")                                # -> brand_not_found
compare_brands(["Audi", "BMW"])
get_common_complaints("Audi", topic_filter="mileage")
get_common_praises("Audi", topic_filter="interior")
get_rating_trends("Audi", year_range=(2015, 2018))
search_reviews("transmission", brand_name="Audi", limit=3)
```

## Testing the full MCP + LLM loop

```bash
source .venv_mcp/bin/activate
python scripts/manual_test.py
```

## What's left

The MCP server and the Ollama-driven chat loop are both fully working
end-to-end today (`scripts/manual_test.py` exercises the real thing). The
only remaining piece is a UI on top of `mcp_server/client.py`'s chat loop
— that's the next thing to build, not yet started.
