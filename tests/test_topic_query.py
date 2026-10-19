"""
Tests for mcp_server/tools/topic_query.py, exercised through the two
public tools that actually call it: get_common_complaints (sentiment=
"negative") and get_common_praises (sentiment="positive"). Audi has
real reviews of both sentiments in this dataset (1055 negative, 4692
positive -- checked directly in aspect_sentiment_table.csv).

Run with:
    pytest tests/test_topic_query.py -v
"""

from __future__ import annotations

from tools.common_complaints import get_common_complaints  # path set up in conftest.py
from tools.common_praises import get_common_praises


def test_get_common_complaints_for_a_known_brand():
    """GOOD: negative-sentiment topics for a brand that genuinely has
    negative reviews."""
    result = get_common_complaints("Audi")

    assert result.status == "ok"
    assert result.sentiment == "negative"
    assert len(result.items) > 0
    assert all(item.count > 0 for item in result.items)


def test_get_common_praises_for_a_known_brand():
    """GOOD: same brand, positive sentiment -- a different tool
    function, same underlying topic_query()."""
    result = get_common_praises("Audi")

    assert result.status == "ok"
    assert result.sentiment == "positive"
    assert len(result.items) > 0


def test_items_are_sorted_with_the_biggest_topic_first():
    """GOOD: topic_query.py sorts by count, descending, before
    truncating to top_n -- the frontend trusts items[0] to be the
    single most-discussed topic."""
    result = get_common_praises("Audi", top_n=5)

    counts = [item.count for item in result.items]
    assert counts == sorted(counts, reverse=True)


def test_top_n_is_respected():
    """GOOD: asking for fewer topics must return fewer topics, not
    silently ignore the limit."""
    result = get_common_praises("Audi", top_n=2)

    assert len(result.items) <= 2


def test_topic_filter_narrows_to_matching_topics_only():
    """GOOD: "mileage" matches real topic labels in this dataset (see
    test_shared.py) -- every item returned must be one of those, not
    some unrelated topic that happens to also be common for Audi."""
    result = get_common_complaints("Audi", topic_filter="mileage")

    assert result.status == "ok"
    assert all("mileage" in item.topic_label.lower() for item in result.items)


def test_unknown_brand_returns_brand_not_found():
    """BAD input: brand not in the dataset."""
    result = get_common_complaints("Toyota")

    assert result.status == "brand_not_found"
    assert result.items == []


def test_unmatched_topic_filter_returns_topic_not_found_with_options():
    """BAD input: a topic_filter that doesn't match anything, real or
    fuzzy, must tell the caller clearly -- and hand back the full list
    of real topics so a human (or the LLM) can pick a valid one next,
    which is exactly what evidence.ts's onOptionClick wires up to."""
    result = get_common_complaints("Audi", topic_filter="xkqzvt_no_such_aspect")

    assert result.status == "topic_not_found"
    assert result.items == []
    assert result.available_topics  # non-empty: real options were offered


def test_valid_brand_and_topic_but_no_matching_reviews_returns_no_results():
    """BAD/edge input: a real brand and a real topic that simply has no
    overlap with it. "allroad" only matches Audi's own wagon topic (see
    phase5_topic_info.csv), and BMW has zero reviews tagged with it --
    note this is NOT the same as topic_not_found: the topic itself is
    perfectly real, there's just nothing for BMW there."""
    result = get_common_complaints("BMW", topic_filter="allroad")

    assert result.status == "no_results"
    assert result.items == []
