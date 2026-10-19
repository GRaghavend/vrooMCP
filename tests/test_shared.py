"""
Tests for mcp_server/tools/shared.py's two pure helper functions:
resolve_brand() and match_topics().

Note on test data: shared.py loads the real CSVs in data/processed/ at
IMPORT time, into module-level variables (KNOWN_BRANDS, topic_info_df,
etc.) -- see shared.py lines 108-118. That data is small (only 5 brands
total) and checked into git, so it's effectively a fixture already:
static, deterministic, and fast to load. We use it directly instead of
building a fake CSV, which would require monkeypatching shared.DATA_DIR
and reloading the module before anything imports it -- extra moving
parts for no real benefit here.

Run with:
    pytest tests/test_shared.py -v
"""

from __future__ import annotations

from tools.shared import KNOWN_BRANDS, match_topics, resolve_brand  # path set up in conftest.py


# ---------------------------------------------------------------------------
# resolve_brand
# ---------------------------------------------------------------------------

def test_resolve_brand_is_case_insensitive():
    """GOOD: lowercase, uppercase, and mixed case all resolve to the one
    canonical spelling stored in the data."""
    assert resolve_brand("audi") == "Audi"
    assert resolve_brand("AUDI") == "Audi"
    assert resolve_brand("AuDi") == "Audi"


def test_resolve_brand_strips_surrounding_whitespace():
    """GOOD: a brand name with stray spaces (e.g. pasted from elsewhere)
    still resolves."""
    assert resolve_brand("  bmw  ") == "BMW"


def test_resolve_brand_returns_none_for_an_unknown_brand():
    """BAD input: a brand that isn't in the dataset at all (e.g. a typo,
    or a brand genuinely not covered) must come back as None -- not
    raise an exception, and not silently return some other brand."""
    assert resolve_brand("Toyota") is None
    assert resolve_brand("totally-not-a-car-brand") is None


def test_resolve_brand_covers_every_known_brand():
    """Sanity check on the test data itself: every brand the dataset
    claims to know about must actually resolve to itself."""
    for brand in KNOWN_BRANDS:
        assert resolve_brand(brand.lower()) == brand


# ---------------------------------------------------------------------------
# match_topics
# ---------------------------------------------------------------------------

def test_match_topics_substring_match():
    """GOOD: "mileage" is a substring of real topic labels in this
    dataset (e.g. "high mileage & maintenance reliability", "fuel
    economy & diesel mileage") -- both should come back."""
    hits = match_topics("mileage")

    assert len(hits) >= 2
    assert all("mileage" in h.lower() for h in hits)


def test_match_topics_is_case_insensitive():
    """GOOD: same query, different case, same result."""
    assert match_topics("MILEAGE") == match_topics("mileage")


def test_match_topics_fuzzy_fallback_for_a_near_miss_spelling():
    """GOOD: no topic label contains this exact string as a substring,
    so this only passes if the fuzzy-matching fallback in shared.py
    (difflib.get_close_matches) is actually working.

    Note: difflib compares the WHOLE query against the WHOLE topic
    label, so the fuzzy fallback only catches a typo that's close to
    an entire label's length (like the one-letter swap below) -- a
    short single-word typo like "milage" for "mileage" does NOT match,
    because its similarity ratio against a 40+ character label is too
    low to clear cutoff=0.4, even though a human reads it instantly.
    That's a real, worth-knowing limitation of this fallback, not a
    bug in this test."""
    hits = match_topics("mercedes-benz brand onwership")  # one letter swapped from the real label

    assert hits
    assert "mercedes-benz brand ownership" in hits


def test_match_topics_returns_empty_list_for_gibberish():
    """BAD input: a query with no reasonable match to anything, fuzzy or
    otherwise, must come back as an empty list -- not raise, not return
    unrelated topics just because they're the "closest available"."""
    assert match_topics("xkqzvt_no_such_aspect") == []


def test_match_topics_returns_empty_list_for_blank_input():
    """BAD input: shared.py explicitly special-cases an empty/whitespace
    topic_filter to return [] immediately, without even querying the
    dataframe."""
    assert match_topics("") == []
    assert match_topics("   ") == []
