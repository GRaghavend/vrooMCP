"""
Shared data layer for all MCP tools: loads the precomputed CSVs once at
import time, exposes the lookup helpers every tool needs (brand
resolution, topic matching), and wraps each tool with structured logging.

Deliberately the single place that touches the DataFrames directly -- each
tools/*.py module reads through the helpers here rather than loading its
own copy of the data.
"""

from __future__ import annotations

import difflib
import functools
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from logging_config import get_logger, log_event, setup_logging, timed, truncate

setup_logging(log_filename="mcp_server.log")
logger = get_logger("data")
tool_logger = get_logger("tools")

# mcp_server/tools/shared.py -> mcp_server/tools -> mcp_server -> repo root
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

REQUIRED_COLUMNS = {
    "brand_stats.csv": {
        "brand_name", "review_count", "avg_rating", "median_rating",
        "rating_std", "avg_car_year",
    },
    "rating_trends.csv": {
        "car_year", "brand_name", "avg_rating", "review_count",
    },
    "cleaned_reviews.csv": {
        "review_id", "brand_name", "car_year", "date", "rating",
        "review_text", "word_count",
    },
    "aspect_sentiment_table.csv": {
        "review_id", "brand_name", "car_year", "Rating",
        "predicted_sentiment", "confidence_score", "topic_id",
        "top_keywords", "topic_label",
    },
    "phase5_topic_info.csv": {
        "topic_id", "review_count", "top_keywords", "topic_label",
    },
}


def _load_csv_or_die(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        log_event(logger, logging.CRITICAL, "app.startup.failed", file=filename, reason="missing")
        sys.exit(f"FATAL: required data file missing: {path}")
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS[filename] - set(df.columns)
    if missing:
        log_event(
            logger, logging.CRITICAL, "app.startup.failed",
            file=filename, reason="missing_columns", missing_columns=sorted(missing),
        )
        sys.exit(f"FATAL: {filename} is missing required columns: {sorted(missing)}")
    log_event(
        logger, logging.INFO, "app.startup.data_loaded",
        file=filename, rows=len(df), columns=list(df.columns),
    )
    return df


def logged_tool(fn):
    """Wrap a tool function with structured start/end/error logging.
    Preserves fn's signature (via functools.wraps -> __wrapped__) so the
    MCP tool decorator still sees the original parameters for schema
    generation."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        call_args = {**dict(zip(fn.__code__.co_varnames, args)), **kwargs}
        log_event(
            tool_logger, logging.INFO, "tool.call.start",
            tool=fn.__name__, arguments={k: truncate(v) for k, v in call_args.items()},
        )
        with timed() as t:
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                log_event(
                    tool_logger, logging.ERROR, "tool.call.error",
                    tool=fn.__name__, error_type=type(exc).__name__, error=str(exc),
                )
                raise
        status = getattr(result, "status", "unknown")
        log_event(
            tool_logger, logging.INFO, "tool.call.end",
            tool=fn.__name__, status=status, duration_ms=t.ms,
        )
        return result

    return wrapper


# ---- Load all data once at import time; fail loudly if anything is wrong --

brand_stats_df = _load_csv_or_die("brand_stats.csv")
rating_trends_df = _load_csv_or_die("rating_trends.csv")
cleaned_reviews_df = _load_csv_or_die("cleaned_reviews.csv")
aspect_sentiment_df = _load_csv_or_die("aspect_sentiment_table.csv")
topic_info_df = _load_csv_or_die("phase5_topic_info.csv")

KNOWN_BRANDS = sorted(brand_stats_df["brand_name"].unique().tolist())
KNOWN_TOPICS = sorted(topic_info_df["topic_label"].dropna().unique().tolist())

# lowercase lookup: brand_key -> canonical brand_name
_BRAND_KEY_MAP = {b.lower(): b for b in KNOWN_BRANDS}


def resolve_brand(brand_name: str) -> Optional[str]:
    """Case-insensitive resolution of a brand name to its canonical form."""
    return _BRAND_KEY_MAP.get(brand_name.strip().lower())


def match_topics(topic_filter: str) -> list[str]:
    """Resolve a free-text topic_filter to known topic_label values.

    Tries substring match against topic_label and top_keywords first
    (cheap, precise for cases like "mileage" -> "... mileage & maintenance
    ..."); falls back to fuzzy string matching against topic_label so
    near-miss spellings still resolve.
    """
    needle = topic_filter.strip().lower()
    if not needle:
        return []

    substring_hits = topic_info_df.loc[
        topic_info_df["topic_label"].str.lower().str.contains(needle, na=False)
        | topic_info_df["top_keywords"].str.lower().str.contains(needle, na=False)
    ]
    if not substring_hits.empty:
        return substring_hits["topic_label"].tolist()

    fuzzy_hits = difflib.get_close_matches(topic_filter, KNOWN_TOPICS, n=5, cutoff=0.4)
    return fuzzy_hits
