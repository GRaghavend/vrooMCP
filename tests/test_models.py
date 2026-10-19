"""
Tests for mcp_server/models.py -- the Pydantic schemas.

A Pydantic model has exactly two jobs: accept good data, reject bad
data. So every test below is one of two shapes:

    GOOD data -> build the model -> no error, fields come back as given
    BAD data  -> build the model -> pydantic.ValidationError is raised

Run with:
    pytest tests/test_models.py -v
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import BrandStats, BrandStatsResult, ChatRequest, ReviewMatch  # path set up in conftest.py


# ---------------------------------------------------------------------------
# ChatRequest -- what the frontend actually sends over HTTP for POST /chat
# ---------------------------------------------------------------------------

def test_chat_request_accepts_a_normal_message():
    """GOOD: a plain message, no conversation_id (i.e. a new chat)."""
    req = ChatRequest(message="What's the most reliable brand?")

    assert req.message == "What's the most reliable brand?"
    assert req.conversation_id is None  # optional field, correctly defaults to None


def test_chat_request_accepts_an_existing_conversation_id():
    """GOOD: a follow-up message in an existing conversation."""
    req = ChatRequest(conversation_id="conv-42", message="And what about BMW?")

    assert req.conversation_id == "conv-42"


def test_chat_request_rejects_empty_message():
    """BAD: message="" violates min_length=1. This is the exact rule
    tests/test_backend_api.py::test_chat_rejects_empty_message relies on
    showing up as an HTTP 422 -- here we check the rule itself, one
    layer lower, with no HTTP involved at all."""
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_rejects_a_missing_message():
    """BAD: message has no default. Leaving it out entirely must fail,
    not silently become None or ''."""
    with pytest.raises(ValidationError):
        ChatRequest()  # no `message=` given at all


# ---------------------------------------------------------------------------
# BrandStats -- the numeric fields mcp_server/tools/brand_stats.py computes
# ---------------------------------------------------------------------------

def test_brand_stats_accepts_well_formed_numbers():
    """GOOD: every field the real tool would produce."""
    stats = BrandStats(
        brand_name="Toyota",
        review_count=120,
        avg_rating=4.3,
        median_rating=4.5,
        rating_std=0.8,
        avg_car_year=2019.5,
    )

    assert stats.review_count == 120
    assert stats.avg_rating == 4.3


def test_brand_stats_rejects_a_non_numeric_rating():
    """BAD: avg_rating must be a number. A string that isn't even
    numeric-looking (unlike "4.3", which pydantic would sensibly coerce
    to 4.3 -- that's a deliberate pydantic convenience, not a bug) must
    fail outright."""
    with pytest.raises(ValidationError):
        BrandStats(
            brand_name="Toyota",
            review_count=120,
            avg_rating="not-a-number",
            median_rating=4.5,
            rating_std=0.8,
            avg_car_year=2019.5,
        )


def test_brand_stats_rejects_a_missing_required_field():
    """BAD: review_count is required. Leaving it out must fail outright
    -- it must NOT silently default to 0, which would quietly hide a
    real bug upstream where the count was never computed."""
    with pytest.raises(ValidationError):
        BrandStats(
            brand_name="Toyota",
            avg_rating=4.3,
            median_rating=4.5,
            rating_std=0.8,
            avg_car_year=2019.5,
        )


# ---------------------------------------------------------------------------
# BrandStatsResult -- exercises the Literal["ok", "brand_not_found"] status
# ---------------------------------------------------------------------------

def test_brand_stats_result_accepts_a_known_status():
    """GOOD: "ok" and "brand_not_found" are the two allowed values."""
    result = BrandStatsResult(status="brand_not_found", brand_name="Toyoat", message="Unknown brand.")

    assert result.status == "brand_not_found"
    assert result.stats is None  # optional, correctly absent on a not-found result


def test_brand_stats_result_rejects_an_unlisted_status():
    """BAD: Literal["ok", "brand_not_found"] means any OTHER string must
    be rejected. This is what would catch a typo like "not_found"
    (missing the "brand_" prefix) before it ships -- a value the
    frontend's isBrandStatsResult() check in evidence.ts has never seen
    and wouldn't know how to render."""
    with pytest.raises(ValidationError):
        BrandStatsResult(status="not_found", brand_name="Toyota")


# ---------------------------------------------------------------------------
# ReviewMatch -- one row of search_reviews.py's output
# ---------------------------------------------------------------------------

def test_review_match_accepts_a_well_formed_row():
    """GOOD."""
    match = ReviewMatch(
        review_id=101,
        brand_name="Honda",
        car_year=2021,
        date="2021-06-15",
        rating=4.0,
        review_text="Great mileage, poor infotainment.",
        word_count=5,
    )

    assert match.car_year == 2021


def test_review_match_rejects_a_non_integer_review_id():
    """BAD: review_id is an id, not free text -- a string that isn't
    even numeric-looking must be rejected, not silently kept as a str."""
    with pytest.raises(ValidationError):
        ReviewMatch(
            review_id="not-an-id",
            brand_name="Honda",
            car_year=2021,
            date="2021-06-15",
            rating=4.0,
            review_text="Great mileage.",
            word_count=3,
        )
