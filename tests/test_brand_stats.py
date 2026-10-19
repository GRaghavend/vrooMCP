"""
Tests for mcp_server/tools/brand_stats.py's get_brand_stats().

Run with:
    pytest tests/test_brand_stats.py -v
"""

from __future__ import annotations

from tools.brand_stats import get_brand_stats  # path set up in conftest.py
from tools.shared import KNOWN_BRANDS, cleaned_reviews_df


def test_get_brand_stats_for_a_known_brand_returns_ok():
    """GOOD: a real brand, written in a casual lowercase form a user
    would actually type."""
    result = get_brand_stats("audi")

    assert result.status == "ok"
    assert result.brand_name == "Audi"  # resolved to the canonical spelling
    assert result.stats is not None
    assert result.stats.review_count > 0
    assert 1.0 <= result.stats.avg_rating <= 5.0  # ratings in this dataset run 1-5


def test_get_brand_stats_matches_a_manual_calculation_from_the_raw_reviews():
    """Cross-check: brand_stats.csv is a PRECOMPUTED summary of
    cleaned_reviews.csv (the raw per-review data). If someone's
    aggregation pipeline changes and the two drift apart, this test
    catches it -- it doesn't depend on hardcoding today's exact number,
    just that the two data files still agree with each other.

    cleaned_reviews.csv deliberately keeps duplicate rows rather than
    hard-deleting them (see eda/EDA_NPL_38K.ipynb), while brand_stats.csv
    was aggregated after dropping duplicates (see eda/EDA.ipynb). So the
    manual calculation here must dedupe the same way before comparing,
    or every brand's count is off by its duplicate-row count."""
    result = get_brand_stats("Audi")

    non_id_columns = [c for c in cleaned_reviews_df.columns if c != "review_id"]
    deduped_reviews = cleaned_reviews_df.drop_duplicates(subset=non_id_columns)
    audi_reviews = deduped_reviews.loc[deduped_reviews["brand_name"] == "Audi"]
    expected_avg = round(float(audi_reviews["rating"].mean()), 3)
    expected_count = len(audi_reviews)

    assert result.stats.review_count == expected_count
    assert result.stats.avg_rating == expected_avg


def test_get_brand_stats_for_an_unknown_brand_returns_brand_not_found():
    """BAD input: a brand not in this dataset (Toyota genuinely isn't
    covered here) must come back as a clear status, with the real list
    of brands the user could ask about instead -- not a crash, and not
    a result that pretends to have real stats."""
    result = get_brand_stats("Toyota")

    assert result.status == "brand_not_found"
    assert result.stats is None
    assert result.brand_name == "Toyota"  # echoes back what the user typed, unresolved
    assert result.available_brands == KNOWN_BRANDS


def test_get_brand_stats_for_an_empty_string_returns_brand_not_found():
    """BAD input: an empty brand name is still just "an unknown brand"
    as far as this tool is concerned -- not a special crash case."""
    result = get_brand_stats("")

    assert result.status == "brand_not_found"
