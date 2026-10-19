"""
Tests for mcp_server/tools/rating_trends.py's get_rating_trends().

Audi's real year range in this dataset is 1997-2018 (checked directly
in data/processed/rating_trends.csv) -- used below for a year_range
filter whose expected row count we can state exactly.

Run with:
    pytest tests/test_rating_trends.py -v
"""

from __future__ import annotations

from tools.rating_trends import get_rating_trends  # path set up in conftest.py


def test_get_rating_trends_for_a_known_brand_returns_sorted_points():
    """GOOD: every point belongs to the requested brand, and points come
    back sorted by year (ascending) -- the frontend's trend chart in
    EvidencePane.tsx assumes that order rather than re-sorting itself."""
    result = get_rating_trends(brand_name="audi")

    assert result.status == "ok"
    assert len(result.points) > 0
    assert all(p.brand_name == "Audi" for p in result.points)

    years = [p.car_year for p in result.points]
    assert years == sorted(years)


def test_get_rating_trends_with_a_year_range_filters_correctly():
    """GOOD: 2000-2005 inclusive for Audi is exactly 6 rows (one per
    year) in the real data -- every point's year must fall in range."""
    result = get_rating_trends(brand_name="Audi", year_range=(2000, 2005))

    assert result.status == "ok"
    assert len(result.points) == 6
    assert all(2000 <= p.car_year <= 2005 for p in result.points)


def test_get_rating_trends_for_an_unknown_brand_returns_brand_not_found():
    """BAD input: an uncovered brand name."""
    result = get_rating_trends(brand_name="Toyota")

    assert result.status == "brand_not_found"
    assert result.points == []


def test_get_rating_trends_with_a_year_range_outside_the_data_returns_no_results():
    """BAD/edge input: a syntactically valid year range that simply has
    no data in it (this dataset has no 1900s car years) must be
    "no_results", not an empty-but-"ok" response or a crash."""
    result = get_rating_trends(brand_name="Audi", year_range=(1900, 1901))

    assert result.status == "no_results"
    assert result.points == []


def test_get_rating_trends_with_no_filters_covers_multiple_brands():
    """GOOD: calling with no brand at all is a valid "give me
    everything" request."""
    result = get_rating_trends()

    assert result.status == "ok"
    brands_seen = {p.brand_name for p in result.points}
    assert len(brands_seen) > 1
