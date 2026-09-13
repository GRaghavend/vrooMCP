"""get_brand_stats tool: average rating, review count, and rating stats for
a single car brand."""

from __future__ import annotations

from models import BrandStats, BrandStatsResult

from .shared import KNOWN_BRANDS, brand_stats_df, logged_tool, resolve_brand


@logged_tool
def get_brand_stats(brand_name: str) -> BrandStatsResult:
    """Get average rating, review count, and rating stats for a single car brand.

    Args:
        brand_name: Brand name, e.g. "BMW" (case-insensitive).
    """
    resolved = resolve_brand(brand_name)
    if resolved is None:
        return BrandStatsResult(
            status="brand_not_found",
            brand_name=brand_name,
            message=f"Unknown brand '{brand_name}'.",
            available_brands=KNOWN_BRANDS,
        )

    row = brand_stats_df.loc[brand_stats_df["brand_name"] == resolved].iloc[0]
    return BrandStatsResult(
        status="ok",
        brand_name=resolved,
        stats=BrandStats(
            brand_name=resolved,
            review_count=int(row["review_count"]),
            avg_rating=round(float(row["avg_rating"]), 3),
            median_rating=round(float(row["median_rating"]), 3),
            rating_std=round(float(row["rating_std"]), 3),
            avg_car_year=round(float(row["avg_car_year"]), 1),
        ),
    )
