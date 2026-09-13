# Sentiment classification

Phase 4 of the pipeline (see the [top-level README](../README.md)):
picks a sentiment model by validating candidates against a gold-labeled
reference set, then applies the winner to the full review dataset. Runs
on Kaggle (GPU) — see `sentimentclassification.ipynb`'s config cell for
the required input layout.

## Validation set vs. actual dataset

Two different files are in play, and they are not interchangeable:

- **Validation set** — `data/raw/3700_review.csv`, 3,700 reviews that
  ship with pre-existing gold labels (`relative sentiments`: negative /
  neutral only — the reference set has **no positive-labeled examples**,
  which the notebook prints a warning about). Used **only** to score
  candidate models; never trained on, never predicted on for the final
  output.
- **Actual dataset** — `data/interim/38000_processed.csv`, the full
  38K-review set. The winning model's predictions on this file are what
  actually flows downstream into `topic_modelling/`.

## Candidate models compared

Four models are scored against the validation set's gold labels
(accuracy, macro-F1, balanced accuracy):

| Model | Type |
|---|---|
| VADER | Rule-based baseline, no GPU needed |
| DistilBERT-SST2 (`distilbert-base-uncased-finetuned-sst-2-english`) | Binary transformer, movie-review domain |
| RoBERTa-3class (`cardiffnlp/twitter-roberta-base-sentiment-latest`) | 3-class transformer, handles neutral + informal text |
| SiEBERT (`siebert/sentiment-roberta-large-english`) | Binary transformer, cross-domain |

Because the binary models (DistilBERT, SiEBERT) can't predict "neutral,"
they're structurally penalized on the ~10% of the gold set labeled
neutral — the notebook prints this caveat explicitly rather than letting
a misleading number stand alone.

**Winner**: `cardiffnlp/twitter-roberta-base-sentiment-latest`, applied to
all 31,938 reviews in Step B.

## Where the results live

- **Comparison table** (all 4 candidates' accuracy/macro-F1/balanced
  accuracy) → `data/interim/phase4_model_comparison.csv`. This is a
  human-readable artifact for picking the winner, not read by any
  downstream code.
- **Final predictions** (winning model applied to the full 38K set:
  `review_id`, `predicted_sentiment`, `confidence_score`) → written to
  Kaggle's working directory as `phase4_sentiment_predictions_38k.csv`,
  then downloaded and placed at `data/interim/phase4_sentiment_predictions_38k.csv`
  to feed `topic_modelling/topicmodelling.ipynb`, which merges it into
  the final `aspect_sentiment_table.csv`.

Since the reference set has no positive-labeled examples, there's no way
to validate the winning model's positive-class behavior here — the topic
modelling notebook adds a proxy sanity check instead (predicted sentiment
vs. average star rating; positive should score highest, negative lowest).
