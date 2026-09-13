"""
One-time offline job: derives data/processed/phase5_topic_info.csv from
data/processed/aspect_sentiment_table.csv (topic_id, topic_label,
top_keywords are already 1:1 per BERTopic topic; this just aggregates
review_count per topic). Run once; the MCP server treats the output as a
static reference file.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

df = pd.read_csv(DATA_DIR / "aspect_sentiment_table.csv")

topic_info = (
    df.groupby(["topic_id", "topic_label"], dropna=False)
    .agg(review_count=("review_id", "count"), top_keywords=("top_keywords", "first"))
    .reset_index()
    .sort_values("review_count", ascending=False)
)

out_path = DATA_DIR / "phase5_topic_info.csv"
topic_info.to_csv(out_path, index=False)
print(f"Wrote {len(topic_info)} topics to {out_path}")
