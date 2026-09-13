# EDA

Exploratory data analysis on the raw car review data, run before any
modeling. This is the first stage of the pipeline described in the
[top-level README](../README.md) — its outputs are the tables everything
downstream (sentiment classification, topic modelling, and ultimately the
MCP server) is built on.

Run these three notebooks first, in this order, from inside this folder
(so their relative `../data/...` paths resolve correctly):

| # | Notebook | Reads | Writes |
|---|---|---|---|
| 1 | `EDA.ipynb` | `../data/raw/38000_review.csv` | `../data/processed/brand_stats.csv`, `../data/processed/rating_trends.csv` |
| 2 | `EDA_NLP_3700.ipynb` | `../data/raw/3700_review.csv` | `../data/processed/reference_validation.csv` |
| 3 | `EDA_NPL_38K.ipynb` | `../data/raw/38000_review.csv`, `../data/interim/38000_processed.csv` | `../data/interim/phase3_38k_flagged.csv`, `../data/processed/cleaned_reviews.csv` |

## 1. `EDA.ipynb` — non-NLP EDA on the full 38K dataset

Establishes the shape of the data before anything else is built on it:
31,938 reviews across 5 luxury brands (Audi, BMW, INFINITI, Lexus,
Mercedes-Benz), rating distribution, brand-wise rating comparison, car-year
coverage (1997–2018), review-length and duplicate checks. Full narrative
and findings are in the notebook's own markdown cells.

**Feeds the MCP server directly**: `brand_stats.csv` and `rating_trends.csv`
are two of the five tables `mcp_server/tools` reads verbatim — they back
the `get_brand_stats`, `compare_brands`, and `get_rating_trends` tools
with no further transformation.

## 2. `EDA_NLP_3700.ipynb` — reference-set validation

A separate 3,700-review sample that already ships with gold
`sentiment_score`/`sentiment_label` values (not used for training). This
notebook checks score/label consistency and word frequency per sentiment
class on that gold set, producing `reference_validation.csv` — a sanity
check used later, in Phase 4, to validate the sentiment classifier
candidates in `sentiment_classification/` before picking a winner. Not
read by the MCP server itself.

## 3. `EDA_NPL_38K.ipynb` — text-quality EDA for the full dataset

NLP-adjacent (but not model-based) EDA on the review text of the full 38K
set: missing/short reviews, word- and character-length distributions,
exact and normalized-text duplicates, and vocabulary size. Flags
problem rows into `phase3_38k_flagged.csv` for manual cleaning review,
then reads back the manually reconciled `38000_processed.csv` and exports
the final `cleaned_reviews.csv`.

**Feeds the MCP server directly**: `cleaned_reviews.csv` backs the
`search_reviews` tool (free-text search over review content).

## Where this leads

Once these three notebooks have run, `data/processed/` holds 3 of the 5
tables the MCP server needs (`brand_stats.csv`, `rating_trends.csv`,
`cleaned_reviews.csv`) plus the validation-only `reference_validation.csv`.
The remaining two (`aspect_sentiment_table.csv`, `phase5_topic_info.csv`)
come from `sentiment_classification/` and `topic_modelling/` — see the
top-level README for the rest of the chain.
