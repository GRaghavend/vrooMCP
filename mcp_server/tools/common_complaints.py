"""get_common_complaints tool: top negative-sentiment review topics for a
brand, optionally narrowed to a specific aspect."""

from __future__ import annotations

from typing import Optional

from models import TopicQueryResult

from .shared import logged_tool
from .topic_query import topic_query


@logged_tool
def get_common_complaints(
    brand_name: str, topic_filter: Optional[str] = None, top_n: int = 5
) -> TopicQueryResult:
    """Get the top negative-sentiment review topics (complaints) for a brand,
    optionally narrowed to a specific aspect via topic_filter.

    Args:
        brand_name: Brand name, e.g. "Honda" (case-insensitive).
        topic_filter: Optional free-text aspect to narrow to, e.g. "mileage".
            Matched (substring, then fuzzy) against known BERTopic labels.
        top_n: Number of top complaint topics to return.
    """
    return topic_query(brand_name, "negative", topic_filter, top_n)
