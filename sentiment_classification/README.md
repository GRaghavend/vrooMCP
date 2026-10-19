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

## Why RoBERTa over VADER, despite VADER's higher score

Read `phase4_model_comparison.csv` on its own and the choice looks wrong:
VADER scores *higher* than the winning RoBERTa-3class model on all three
metrics (accuracy 0.99 vs 0.86, macro-F1 0.66 vs 0.47, balanced accuracy
0.99 vs 0.75). If someone opens that CSV without more context, "why not
just use VADER" is the obvious question.

The reason is that VADER's score here is **circular** — the gold labels
it's being judged against were generated *from VADER itself*:

- `data/raw/3700_review.csv` ships two relevant columns: `sentiment score`
  (VADER's raw `{neg, neu, pos, compound}` output) and `relative
  sentiments` (the "gold" label used to score every candidate).
- `data/processed/reference_validation.csv` is the same thing in a
  cleaner shape: `score_compound` + `sentiment_label`.
- Recomputing a label from the stored compound score using the exact
  threshold rule the notebook's own `vader_predict()` uses (`>= 0.05` →
  positive, `<= -0.05` → negative, else neutral) and comparing it to the
  "gold" `relative sentiments` / `sentiment_label` column gives **100%
  agreement — 0 mismatches across all 3,700 rows**.

In other words, the reference labels aren't independent ground truth —
they're VADER's own compound score, thresholded and renamed. Scoring
VADER against them is VADER grading its own homework; its 0.99 accuracy
says "VADER agrees with VADER," not "VADER understands car reviews."
RoBERTa-3class, DistilBERT, and SiEBERT are the only candidates here
actually being judged against an external rule rather than their own
output, so their (lower, honest) numbers are the only ones worth
comparing to each other.

That still leaves the binary-vs-3-class asymmetry noted above (DistilBERT
and SiEBERT structurally can't score a true "neutral" and are penalized
for it on the ~10% of the set labeled neutral), so even among the three
non-circular candidates this isn't a perfectly fair bake-off. RoBERTa-3class
was picked because it's the only one that's both 3-class (so it can
actually express "neutral" instead of being forced to guess positive/
negative) and trained on short, informal social-text (Twitter), which is
closer in register to car reviews than DistilBERT-SST2's movie-review
training domain.

**Takeaway for defending this choice**: don't cite the macro-F1 ranking at
face value — lead with the circularity finding above. It's the real
reason VADER's number can't be trusted, independent of whether RoBERTa
"won" a fair fight.

**Provenance**: `relative sentiments` and `sentiment score` are not
computed anywhere in this repo's own pipeline — they ship pre-existing in
the raw input file, `data/raw/3700_review.csv` (see `eda/EDA_NLP_3700.ipynb`'s
config cell, which reads both as already-present columns). `EDA_NLP_3700.ipynb`
already has a "Score vs label consistency" check (the `flag_mismatch` cell)
that looks for rows where the label says negative but the compound score
is positive — i.e. the one-directional case of exactly this issue was
already being watched for at the EDA stage. What wasn't written down
until now is the full picture: checked against the same three-way
threshold the phase-4 notebook itself uses for VADER, the label and the
score agree on *every single row*, which is what makes VADER's phase-4
number circular rather than just "pretty good."
