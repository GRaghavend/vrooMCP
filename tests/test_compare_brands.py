"""
Tests for mcp_server/tools/compare_brands.py's compare_brands().

compare_brands() is a thin composition over get_brand_stats() (see its
own docstring) -- so the one thing genuinely worth locking in here is
that composition: a request mixing one real and one fake brand must
give a real result for the real one AND a clean not-found for the fake
one, in the same response -- not let one bad name blow up the whole
call.

Run with:
    pytest tests/test_compare_brands.py -v
"""

from __future__ import annotations

from tools.compare_brands import compare_brands  # path set up in conftest.py


def test_compare_brands_with_two_known_brands():
    """GOOD: both brands resolve, both come back "ok"."""
    result = compare_brands(["Audi", "BMW"])

    assert set(result.brands.keys()) == {"Audi", "BMW"}
    assert result.brands["Audi"].status == "ok"
    assert result.brands["BMW"].status == "ok"
    assert result.brands["Audi"].stats.brand_name == "Audi"


def test_compare_brands_with_one_known_and_one_unknown_brand():
    """MIXED good/bad: this is the case that would be easy to get wrong
    -- e.g. one exception anywhere in the loop taking down the whole
    comparison. The known brand must still come back "ok" even though
    its neighbor in the same request is nonsense."""
    result = compare_brands(["Audi", "Toyota"])

    assert result.brands["Audi"].status == "ok"
    assert result.brands["Toyota"].status == "brand_not_found"
    assert result.brands["Toyota"].available_brands  # still gets a helpful brand list


def test_compare_brands_with_a_single_brand():
    """GOOD: compare_brands doesn't actually require 2+ brands -- a
    list of one is a degenerate but valid comparison."""
    result = compare_brands(["Lexus"])

    assert list(result.brands.keys()) == ["Lexus"]
    assert result.brands["Lexus"].status == "ok"


def test_compare_brands_with_an_empty_list():
    """BAD/edge input: no brands requested at all must give an empty
    comparison, not an error."""
    result = compare_brands([])

    assert result.brands == {}
