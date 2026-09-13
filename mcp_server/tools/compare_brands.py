"""compare_brands tool: overall stats for two or more car brands, side by
side. Composes get_brand_stats rather than querying the DataFrame itself."""

from __future__ import annotations

from models import CompareBrandsResult

from .brand_stats import get_brand_stats
from .shared import logged_tool


@logged_tool
def compare_brands(brand_names: list[str]) -> CompareBrandsResult:
    """Compare overall stats for two or more car brands, side by side.

    Args:
        brand_names: List of brand names, e.g. ["Audi", "BMW"].
    """
    return CompareBrandsResult(
        brands={name: get_brand_stats(name) for name in brand_names}
    )
