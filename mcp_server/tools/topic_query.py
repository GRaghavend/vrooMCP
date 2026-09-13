"""Shared query logic behind get_common_complaints and get_common_praises --
not a tool itself, just the common implementation the two tools call with a
different `sentiment` value."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from models import TopicItem, TopicQueryResult

from .shared import KNOWN_BRANDS, KNOWN_TOPICS, aspect_sentiment_df, match_topics, resolve_brand


def topic_query(brand_name: str, sentiment: str, topic_filter: Optional[str], top_n: int) -> TopicQueryResult:
    """For a given brand, find its top review topics (optionally narrowed
    to one topic_filter, e.g. "mileage"), returning a clear status if the
    brand/topic isn't recognized or no matching reviews exist."""
    resolved = resolve_brand(brand_name)
    if resolved is None:
        return TopicQueryResult(
            status="brand_not_found",
            brand_name=brand_name,
            sentiment=sentiment,
            topic_filter=topic_filter,
            message=f"Unknown brand '{brand_name}'.",
            available_brands=KNOWN_BRANDS,
        )

    subset = aspect_sentiment_df.loc[
        (aspect_sentiment_df["brand_name"] == resolved)
        & (aspect_sentiment_df["predicted_sentiment"] == sentiment)
    ]

    matched_topics: Optional[list[str]] = None
    if topic_filter:
        matched_topics = match_topics(topic_filter)
        if not matched_topics:
            return TopicQueryResult(
                status="topic_not_found",
                brand_name=resolved,
                sentiment=sentiment,
                topic_filter=topic_filter,
                message=f"No known topic matches '{topic_filter}'.",
                available_topics=KNOWN_TOPICS,
            )
        subset = subset.loc[subset["topic_label"].isin(matched_topics)]

    if subset.empty:
        return TopicQueryResult(
            status="no_results",
            brand_name=resolved,
            sentiment=sentiment,
            topic_filter=topic_filter,
            message=(
                f"No {sentiment} reviews found for '{resolved}'"
                + (f" matching topic '{topic_filter}'." if topic_filter else ".")
            ),
            available_topics=KNOWN_TOPICS if topic_filter else None,
        )

    grouped = (
        subset.groupby("topic_label")
        .agg(count=("review_id", "count"), topic_id=("topic_id", "first"),
             top_keywords=("top_keywords", "first"))
        .reset_index()
        .sort_values("count", ascending=False)
        .head(top_n)
    )

    items = [
        TopicItem(
            topic_label=row["topic_label"],
            topic_id=row["topic_id"] if pd.notna(row["topic_id"]) else None,
            count=int(row["count"]),
            top_keywords=row["top_keywords"],
        )
        for _, row in grouped.iterrows()
    ]

    return TopicQueryResult(
        status="ok",
        brand_name=resolved,
        sentiment=sentiment,
        topic_filter=topic_filter,
        items=items,
    )
