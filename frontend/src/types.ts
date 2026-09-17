/**
 * Mirrors mcp_server/models.py. Kept in one file, by hand, for the same
 * reason models.py gives as its own single-source-of-truth rationale:
 * these shapes should change only when the backend's do.
 */

export type ToolStatus = "ok" | "brand_not_found" | "topic_not_found" | "no_results" | "error";

export interface BrandStats {
  brand_name: string;
  review_count: number;
  avg_rating: number;
  median_rating: number;
  rating_std: number;
  avg_car_year: number;
}

export interface BrandStatsResult {
  status: ToolStatus;
  brand_name: string;
  stats?: BrandStats | null;
  message?: string | null;
  available_brands?: string[] | null;
}

export interface CompareBrandsResult {
  brands: Record<string, BrandStatsResult>;
}

export interface TopicItem {
  topic_label: string;
  topic_id?: number | null;
  count: number;
  top_keywords: string;
}

export interface TopicQueryResult {
  status: ToolStatus;
  brand_name: string;
  sentiment: "positive" | "negative";
  topic_filter?: string | null;
  items: TopicItem[];
  message?: string | null;
  available_brands?: string[] | null;
  available_topics?: string[] | null;
}

export interface RatingTrendPoint {
  brand_name: string;
  car_year: number;
  avg_rating: number;
  review_count: number;
}

export interface RatingTrendsResult {
  status: ToolStatus;
  points: RatingTrendPoint[];
  message?: string | null;
  available_brands?: string[] | null;
}

export interface ReviewMatch {
  review_id: number;
  brand_name: string;
  car_year: number;
  date: string;
  rating: number;
  review_text: string;
  word_count: number;
}

export interface SearchReviewsResult {
  status: ToolStatus;
  query: string;
  brand_name?: string | null;
  min_rating?: number | null;
  matches: ReviewMatch[];
  message?: string | null;
  available_brands?: string[] | null;
}

// ---- Chat contract (FE <-> BE), see mcp_server/models.py -------------------

export type ToolResult =
  | BrandStatsResult
  | CompareBrandsResult
  | TopicQueryResult
  | RatingTrendsResult
  | SearchReviewsResult
  | Record<string, unknown>;

export interface ToolCallLog {
  tool_name: string;
  arguments: Record<string, unknown>;
  result: ToolResult;
  status: string;
  duration_ms: number;
}

export interface ChatRequest {
  conversation_id?: string | null;
  message: string;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer_text: string;
  tool_calls: ToolCallLog[];
  status: "ok" | "error" | "needs_clarification";
}

export interface HealthResponse {
  status: "ok" | "unavailable";
  mcp_connected: boolean;
  tool_count: number;
}

// ---- UI-only types ----------------------------------------------------

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  toolCalls?: ToolCallLog[];
  turnStatus?: ChatResponse["status"];
}
