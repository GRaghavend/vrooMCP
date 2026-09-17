import type {
  BrandStats,
  BrandStatsResult,
  CompareBrandsResult,
  RatingTrendPoint,
  RatingTrendsResult,
  ReviewMatch,
  SearchReviewsResult,
  ToolCallLog,
  TopicItem,
  TopicQueryResult,
} from "./types";

export interface StatsEntry {
  brand_name: string;
  stats: BrandStats;
}

export interface TopicGroup {
  brand_name: string;
  sentiment: "positive" | "negative";
  topic_filter?: string | null;
  items: TopicItem[];
}

export interface StatusItem {
  toolName: string;
  status: string;
  title: string;
  body: string;
  options: string[];
  onOptionClick?: (option: string) => string; // returns the follow-up question text
}

export type EvidenceSection =
  | { kind: "stats-single"; entry: StatsEntry }
  | { kind: "stats-multi"; entries: StatsEntry[] }
  | { kind: "topics"; groups: TopicGroup[] }
  | { kind: "trend"; brands: string[]; points: RatingTrendPoint[] }
  | { kind: "reviews"; query: string; matches: ReviewMatch[] }
  | { kind: "status"; items: StatusItem[] };

function isBrandStatsResult(v: unknown): v is BrandStatsResult {
  return !!v && typeof v === "object" && "brand_name" in v && "status" in v && !("brands" in v);
}

function isCompareBrandsResult(v: unknown): v is CompareBrandsResult {
  return !!v && typeof v === "object" && "brands" in v;
}

function isTopicQueryResult(v: unknown): v is TopicQueryResult {
  return !!v && typeof v === "object" && "sentiment" in v;
}

function isRatingTrendsResult(v: unknown): v is RatingTrendsResult {
  return !!v && typeof v === "object" && "points" in v;
}

function isSearchReviewsResult(v: unknown): v is SearchReviewsResult {
  return !!v && typeof v === "object" && "matches" in v;
}

/**
 * Turns one turn's raw tool_calls (as returned by POST /chat) into
 * renderable evidence-panel sections. Every field used here comes
 * straight from mcp_server/models.py result shapes -- nothing here
 * invents data the backend didn't return.
 */
export function buildEvidenceSections(toolCalls: ToolCallLog[]): EvidenceSection[] {
  const statsEntries: StatsEntry[] = [];
  const topicGroups: TopicGroup[] = [];
  const trendPoints: RatingTrendPoint[] = [];
  const reviewMatches: ReviewMatch[] = [];
  let reviewQuery = "";
  const statusItems: StatusItem[] = [];

  const addBrandStatsStatus = (toolName: string, result: BrandStatsResult) => {
    if (result.status === "ok" && result.stats) {
      statsEntries.push({ brand_name: result.brand_name, stats: result.stats });
      return;
    }
    statusItems.push({
      toolName,
      status: result.status,
      title: `"${result.brand_name}" is not a covered brand`,
      body: result.message || `${toolName} returned ${result.status}.`,
      options: result.available_brands ?? [],
      onOptionClick: (brand) => `What are the stats for ${brand}?`,
    });
  };

  for (const call of toolCalls) {
    const { tool_name, result } = call;

    if (tool_name === "get_brand_stats" && isBrandStatsResult(result)) {
      addBrandStatsStatus(tool_name, result);
      continue;
    }

    if (tool_name === "compare_brands" && isCompareBrandsResult(result)) {
      for (const brandResult of Object.values(result.brands)) {
        addBrandStatsStatus(tool_name, brandResult);
      }
      continue;
    }

    if (
      (tool_name === "get_common_complaints" || tool_name === "get_common_praises") &&
      isTopicQueryResult(result)
    ) {
      if (result.status === "ok" && result.items.length) {
        topicGroups.push({
          brand_name: result.brand_name,
          sentiment: result.sentiment,
          topic_filter: result.topic_filter,
          items: result.items,
        });
      } else if (result.status === "topic_not_found") {
        statusItems.push({
          toolName: tool_name,
          status: result.status,
          title: `No topic matches "${result.topic_filter ?? ""}"`,
          body: result.message || "That aspect doesn't match any known review topic.",
          options: result.available_topics ?? [],
          onOptionClick: (topic) =>
            result.sentiment === "negative"
              ? `What do ${result.brand_name} owners complain about regarding ${topic}?`
              : `What do ${result.brand_name} owners praise about ${topic}?`,
        });
      } else {
        statusItems.push({
          toolName: tool_name,
          status: result.status,
          title:
            result.status === "brand_not_found"
              ? `"${result.brand_name}" is not a covered brand`
              : `No ${result.sentiment} reviews found`,
          body: result.message || `${tool_name} returned ${result.status}.`,
          options: result.available_brands ?? [],
          onOptionClick: (brand) =>
            result.sentiment === "negative"
              ? `What do ${brand} owners complain about?`
              : `What do ${brand} owners praise?`,
        });
      }
      continue;
    }

    if (tool_name === "get_rating_trends" && isRatingTrendsResult(result)) {
      if (result.status === "ok" && result.points.length) {
        trendPoints.push(...result.points);
      } else {
        statusItems.push({
          toolName: tool_name,
          status: result.status,
          title: result.status === "brand_not_found" ? "Unknown brand" : "No trend data",
          body: result.message || `${tool_name} returned ${result.status}.`,
          options: result.available_brands ?? [],
          onOptionClick: (brand) => `Rating trend for ${brand}`,
        });
      }
      continue;
    }

    if (tool_name === "search_reviews" && isSearchReviewsResult(result)) {
      if (result.status === "ok" && result.matches.length) {
        reviewMatches.push(...result.matches);
        reviewQuery = result.query;
      } else {
        statusItems.push({
          toolName: tool_name,
          status: result.status,
          title: result.status === "brand_not_found" ? "Unknown brand" : "No matching reviews",
          body: result.message || `${tool_name} returned ${result.status}.`,
          options: result.available_brands ?? [],
          onOptionClick: (brand) => `Search reviews mentioning ${result.query} for ${brand}`,
        });
      }
      continue;
    }

    // Unrecognized/error tool call: still surface something rather than
    // silently dropping it.
    if (call.status !== "ok") {
      statusItems.push({
        toolName: tool_name,
        status: call.status,
        title: `${tool_name} failed`,
        body:
          typeof result === "object" && result && "message" in result
            ? String((result as { message?: unknown }).message ?? "Unknown error")
            : "The tool call did not complete successfully.",
        options: [],
      });
    }
  }

  const sections: EvidenceSection[] = [];

  if (statsEntries.length === 1) {
    sections.push({ kind: "stats-single", entry: statsEntries[0] });
  } else if (statsEntries.length > 1) {
    sections.push({ kind: "stats-multi", entries: statsEntries });
  }

  if (topicGroups.length) {
    sections.push({ kind: "topics", groups: topicGroups });
  }

  if (trendPoints.length) {
    const brands = Array.from(new Set(trendPoints.map((p) => p.brand_name)));
    sections.push({ kind: "trend", brands, points: trendPoints });
  }

  if (reviewMatches.length) {
    sections.push({ kind: "reviews", query: reviewQuery, matches: reviewMatches });
  }

  if (statusItems.length) {
    sections.push({ kind: "status", items: statusItems });
  }

  return sections;
}

export function evidenceTitle(sections: EvidenceSection[]): string {
  if (!sections.length) return "No evidence yet";
  const parts: string[] = [];
  for (const s of sections) {
    if (s.kind === "stats-single") parts.push(s.entry.brand_name);
    else if (s.kind === "stats-multi") parts.push(s.entries.map((e) => e.brand_name).join(" vs "));
    else if (s.kind === "topics") parts.push(Array.from(new Set(s.groups.map((g) => g.brand_name))).join(" vs "));
    else if (s.kind === "trend") parts.push(s.brands.join(" vs "));
    else if (s.kind === "reviews") parts.push(`"${s.query}"`);
  }
  return parts.length ? parts.join(" · ") : "Status";
}
