"""
Tests for mcp_server/tools/search_reviews.py's search_reviews().

"engine" is a real, common word in this dataset's review text (4729
matches overall, 1139 of them for Audi -- checked directly in
cleaned_reviews.csv), so it's a safe, non-flaky choice for a "good"
search query that will keep matching even if the data is regenerated,
as long as people keep writing car reviews that mention engines.

Run with:
    pytest tests/test_search_reviews.py -v
"""

from __future__ import annotations

from tools.search_reviews import search_reviews  # path set up in conftest.py


def test_search_reviews_finds_matches_for_a_common_word():
    """GOOD: a query that genuinely appears in review text."""
    result = search_reviews(query="engine")

    assert result.status == "ok"
    assert len(result.matches) > 0
    assert all("engine" in m.review_text.lower() for m in result.matches)


def test_search_reviews_is_case_insensitive():
    """GOOD: the tool's docstring promises case-insensitive matching --
    this pins that promise down."""
    assert search_reviews(query="ENGINE").matches == search_reviews(query="engine").matches


def test_search_reviews_filters_by_brand():
    """GOOD: combining a query with a brand filter must narrow results
    to ONLY that brand, not just prefer it."""
    result = search_reviews(query="engine", brand_name="audi")

    assert result.status == "ok"
    assert len(result.matches) > 0
    assert all(m.brand_name == "Audi" for m in result.matches)


def test_search_reviews_filters_by_minimum_rating():
    """GOOD: every match's rating must be >= the requested floor."""
    result = search_reviews(query="engine", min_rating=4.5)

    assert result.status == "ok"
    assert all(m.rating >= 4.5 for m in result.matches)


def test_search_reviews_respects_the_limit():
    """GOOD: "engine" alone matches thousands of rows -- limit=3 must
    cap the response at 3, not return everything and let the caller
    (or worse, the LLM's context window) deal with it."""
    result = search_reviews(query="engine", limit=3)

    assert len(result.matches) == 3


def test_search_reviews_with_no_matches_returns_no_results():
    """BAD input: a query string that (almost certainly) appears in no
    review, ever."""
    result = search_reviews(query="xkqzvt_this_string_will_never_appear")

    assert result.status == "no_results"
    assert result.matches == []


def test_search_reviews_with_an_unknown_brand_returns_brand_not_found():
    """BAD input: brand filter that isn't in the dataset -- must fail
    on the brand, even though the query itself ("engine") would
    otherwise match plenty of reviews."""
    result = search_reviews(query="engine", brand_name="Toyota")

    assert result.status == "brand_not_found"
    assert result.matches == []
