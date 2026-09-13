"""Pydantic schemas for the Car Reviews Insight MCP server.

Every tool's input and output is typed here so the LLM and any frontend
have a stable contract instead of raw DataFrames or loosely-typed dicts.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# get_brand_stats
# ---------------------------------------------------------------------------

class BrandStats(BaseModel):
    brand_name: str
    review_count: int
    avg_rating: float
    median_rating: float
    rating_std: float
    avg_car_year: float


class BrandStatsResult(BaseModel):
    status: Literal["ok", "brand_not_found"]
    brand_name: str
    stats: Optional[BrandStats] = None
    message: Optional[str] = None
    available_brands: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# compare_brands
# ---------------------------------------------------------------------------

class CompareBrandsResult(BaseModel):
    brands: dict[str, BrandStatsResult]


# ---------------------------------------------------------------------------
# get_common_complaints / get_common_praises
# ---------------------------------------------------------------------------

class TopicItem(BaseModel):
    topic_label: str
    topic_id: Optional[float] = None
    count: int
    top_keywords: str


class TopicQueryResult(BaseModel):
    status: Literal["ok", "brand_not_found", "no_results", "topic_not_found"]
    brand_name: str
    sentiment: Literal["positive", "negative"]
    topic_filter: Optional[str] = None
    items: list[TopicItem] = Field(default_factory=list)
    message: Optional[str] = None
    available_brands: Optional[list[str]] = None
    available_topics: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# get_rating_trends
# ---------------------------------------------------------------------------

class RatingTrendPoint(BaseModel):
    brand_name: str
    car_year: int
    avg_rating: float
    review_count: int


class RatingTrendsResult(BaseModel):
    status: Literal["ok", "brand_not_found", "no_results"]
    points: list[RatingTrendPoint] = Field(default_factory=list)
    message: Optional[str] = None
    available_brands: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# search_reviews
# ---------------------------------------------------------------------------

class ReviewMatch(BaseModel):
    review_id: int
    brand_name: str
    car_year: int
    date: str
    rating: float
    review_text: str
    word_count: int


class SearchReviewsResult(BaseModel):
    status: Literal["ok", "brand_not_found", "no_results"]
    query: str
    brand_name: Optional[str] = None
    min_rating: Optional[float] = None
    matches: list[ReviewMatch] = Field(default_factory=list)
    message: Optional[str] = None
    available_brands: Optional[list[str]] = None


# Note: there are no separate "tool input" Pydantic models here. Each tool
# function's own type-hinted signature in mcp_server.py IS the input
# schema -- the MCPServer machinery derives JSON schema from it directly
# and publishes it via list_tools(), and mcp_server.py's own tool
# functions validate incoming arguments against that same schema before
# running. Duplicating that as a second set of models here (as an earlier,
# pre-MCP version of this file did) would just be two sources of truth
# drifting apart.


# ---------------------------------------------------------------------------
# Chat contract (FE <-> BE)
# ---------------------------------------------------------------------------

class ToolCallLog(BaseModel):
    tool_name: str
    arguments: dict
    result: dict
    status: str
    duration_ms: float


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(
        None, description="Existing conversation id, or omit/null to start a new conversation."
    )
    message: str = Field(..., min_length=1, description="The user's chat message.")


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer_text: str
    tool_calls: list[ToolCallLog] = Field(default_factory=list)
    status: Literal["ok", "error", "needs_clarification"]
