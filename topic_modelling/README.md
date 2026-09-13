# Topic modelling

Phase 5 of the pipeline (see the [top-level README](../README.md)): runs
BERTopic over the review text, attaches sentiment predictions from
`sentiment_classification/`, and produces the final table the MCP server's
`get_common_complaints`/`get_common_praises` tools query. Runs on Kaggle
(GPU) — see `topicmodelling.ipynb`'s config cell for the required input
layout.

## Pipeline

1. Fit BERTopic (`all-MiniLM-L6-v2` embeddings) over every review with
   more than `MIN_WORD_COUNT` (3) words — 38K reviews minus the very
   short ones, which are excluded as too noisy for topic assignment and
   labeled `"Not analyzed (review too short)"` in the final table instead
   of silently dropped.
2. Reduce to `TARGET_TOPIC_COUNT` (40) topics for interpretability, then
   run BERTopic's outlier-reduction pass to reassign as many `-1`
   (unclassified) documents as possible to a real topic.
3. Re-derive keyword representations with a custom vectorizer (stopwords +
   brand names stripped, 1–3 word phrases allowed) so `top_keywords`
   reads cleanly.
4. **Human labeling step** (`TOPIC_LABEL_MAP`, hardcoded in the notebook):
   after inspecting the keyword-only `phase5_topic_info.csv`, each numeric
   `topic_id` is manually assigned a short, human-readable label — e.g.
   topic 4 → `"high mileage & maintenance reliability"`. This is a
   deliberate step, not automated; BERTopic's raw keyword lists aren't
   what gets matched against a user's free-text `topic_filter` in the MCP
   server, the human labels are.
5. Merge topic assignments + sentiment predictions + brand/year/rating
   metadata into the final `aspect_sentiment_table.csv`.

## The 39 human-labeled topics (+ 1 outlier bucket = 40 rows total)

`TOPIC_LABEL_MAP` assigns human-readable labels to **39 topics**
(`topic_id` 0–38, e.g. `"bmw 3 series & sedan driving dynamics"`,
`"ride comfort & suspension smoothness"`, `"electric vehicle range &
charging infrastructure"`). BERTopic's `topic_id = -1` — the bucket for
documents that stayed unclassified even after outlier reduction — is kept
as a distinct 40th row labeled `"No clear topic"` rather than merged into
one of the 39 or dropped, so downstream tools can distinguish "no topic
found" from "topic not asked for."

This is why `data/processed/phase5_topic_info.csv` has **40 rows**: 39
human-labeled topics + 1 outlier row. Both `get_common_complaints` and
`get_common_praises` in `mcp_server/` match a caller's `topic_filter`
against these 39 real labels (substring, then fuzzy match) — see the
top-level README's "`topic_filter` matching" section.

## Where the results live

- `phase5_topic_info.csv` — one row per topic (`topic_id`, `topic_label`,
  `top_keywords`, `review_count`). Two producers write this file:
  the Kaggle notebook itself (downloaded to `data/processed/`), and
  `build_topic_info.py`, a small **local, deterministic** script that
  re-derives the same file directly from `aspect_sentiment_table.csv`
  without needing to re-run BERTopic:

  ```bash
  python topic_modelling/build_topic_info.py
  ```

- `aspect_sentiment_table.csv` — one row per review, with its assigned
  `topic_id`/`topic_label`/`top_keywords` and `predicted_sentiment` from
  `sentiment_classification/`. This is the table `get_common_complaints`
  and `get_common_praises` actually query. Written to Kaggle's working
  directory, then downloaded and placed at `data/processed/`.

## Sanity check

The notebook's last cell cross-tabs `predicted_sentiment` against average
star rating as a proxy check — since the sentiment validation set had no
positive-labeled examples (see `sentiment_classification/README.md`),
this is the only signal available that the "positive" class is behaving
correctly at scale: it should have the highest average rating, "negative"
the lowest.
