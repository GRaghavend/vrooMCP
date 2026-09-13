"""search_reviews tool: keyword/substring search over raw review text, with
optional brand and minimum-rating filters."""

from __future__ import annotations

from typing import Optional

from models import ReviewMatch, SearchReviewsResult

from .shared import KNOWN_BRANDS, cleaned_reviews_df, logged_tool, resolve_brand


@logged_tool
def search_reviews(
    query: str,
    brand_name: Optional[str] = None,
    min_rating: Optional[float] = None,
    limit: int = 20,
) -> SearchReviewsResult:
    """Keyword/substring search over raw review text, with optional brand and
    minimum-rating filters.

    Args:
        query: Free-text substring to search for in review_text (case-insensitive).
        brand_name: Optional brand name to filter to (case-insensitive).
        min_rating: Optional minimum rating filter (inclusive).
        limit: Maximum number of matching reviews to return.
    """
    resolved = None
    if brand_name:
        resolved = resolve_brand(brand_name)
        if resolved is None:
            return SearchReviewsResult(
                status="brand_not_found",
                query=query,
                brand_name=brand_name,
                min_rating=min_rating,
                message=f"Unknown brand '{brand_name}'.",
                available_brands=KNOWN_BRANDS,
            )

    df = cleaned_reviews_df
    df = df.loc[df["review_text"].str.contains(query, case=False, na=False, regex=False)]
    if resolved:
        df = df.loc[df["brand_name"] == resolved]
    if min_rating is not None:
        df = df.loc[df["rating"] >= min_rating]

    if df.empty:
        return SearchReviewsResult(
            status="no_results",
            query=query,
            brand_name=resolved,
            min_rating=min_rating,
            message=f"No reviews found matching '{query}' with the given filters.",
        )

    df = df.head(limit)
    matches = [
        ReviewMatch(
            review_id=int(row["review_id"]),
            brand_name=row["brand_name"],
            car_year=int(row["car_year"]),
            date=str(row["date"]),
            rating=float(row["rating"]),
            review_text=row["review_text"],
            word_count=int(row["word_count"]),
        )
        for _, row in df.iterrows()
    ]
    return SearchReviewsResult(
        status="ok", query=query, brand_name=resolved, min_rating=min_rating, matches=matches
    )
