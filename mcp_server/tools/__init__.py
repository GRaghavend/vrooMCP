"""The 6 MCP tools, one module each. Each tool function is a plain,
undecorated-by-the-server Python function (wrapped only with
`shared.logged_tool`) so it stays independently importable and unit
testable; `server.py` is the only place that registers them with the
MCPServer instance."""

from .brand_stats import get_brand_stats
from .common_complaints import get_common_complaints
from .common_praises import get_common_praises
from .compare_brands import compare_brands
from .rating_trends import get_rating_trends
from .search_reviews import search_reviews

__all__ = [
    "get_brand_stats",
    "compare_brands",
    "get_common_complaints",
    "get_common_praises",
    "get_rating_trends",
    "search_reviews",
]
