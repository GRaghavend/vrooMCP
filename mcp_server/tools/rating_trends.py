"""get_rating_trends tool: average rating by model year, optionally
filtered by brand and/or a year range."""

from __future__ import annotations

from typing import Optional

from models import RatingTrendPoint, RatingTrendsResult

from .shared import KNOWN_BRANDS, logged_tool, rating_trends_df, resolve_brand


@logged_tool
def get_rating_trends(
    brand_name: Optional[str] = None, year_range: Optional[tuple[int, int]] = None
) -> RatingTrendsResult:
    """Get average rating by model year, optionally filtered by brand and/or
    a year range.

    Args:
        brand_name: Optional brand name to filter to (case-insensitive).
        year_range: Optional (start_year, end_year) inclusive filter.
    """
    df = rating_trends_df

    if brand_name:
        resolved = resolve_brand(brand_name)
        if resolved is None:
            return RatingTrendsResult(
                status="brand_not_found",
                message=f"Unknown brand '{brand_name}'.",
                available_brands=KNOWN_BRANDS,
            )
        df = df.loc[df["brand_name"] == resolved]

    if year_range:
        start, end = year_range
        df = df.loc[(df["car_year"] >= start) & (df["car_year"] <= end)]

    df = df.sort_values(["brand_name", "car_year"])

    if df.empty:
        return RatingTrendsResult(
            status="no_results",
            message="No rating trend data matches the given filters.",
        )

    points = [
        RatingTrendPoint(
            brand_name=row["brand_name"],
            car_year=int(row["car_year"]),
            avg_rating=round(float(row["avg_rating"]), 3),
            review_count=int(row["review_count"]),
        )
        for _, row in df.iterrows()
    ]
    return RatingTrendsResult(status="ok", points=points)
