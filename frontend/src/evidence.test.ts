/**
 * Tests for evidence.ts -- turns raw tool_calls (as returned by
 * POST /chat) into the sections the EvidencePane actually renders.
 *
 * No backend, no browser, no React needed here: buildEvidenceSections
 * and evidenceTitle are plain functions, so we just call them with
 * hand-built fake tool_calls (shaped exactly like mcp_server/models.py's
 * real result types) and check what comes back.
 *
 * Run with:
 *   npm test                 (from frontend/)
 */
import { describe, expect, it } from "vitest";
import { buildEvidenceSections, evidenceTitle } from "./evidence";
import type { ToolCallLog } from "./types";

/** Minimal helper: most of ToolCallLog's fields don't matter to
 * buildEvidenceSections, only tool_name/result/status do -- this just
 * saves repeating arguments/duration_ms in every test case below. */
function toolCall(overrides: Partial<ToolCallLog> & Pick<ToolCallLog, "tool_name" | "result">): ToolCallLog {
  return { arguments: {}, status: "ok", duration_ms: 1, ...overrides };
}

describe("buildEvidenceSections", () => {
  it("turns a successful get_brand_stats into a stats-single section", () => {
    const sections = buildEvidenceSections([
      toolCall({
        tool_name: "get_brand_stats",
        result: {
          status: "ok",
          brand_name: "Audi",
          stats: {
            brand_name: "Audi",
            review_count: 6034,
            avg_rating: 4.465,
            median_rating: 4.75,
            rating_std: 0.783,
            avg_car_year: 2006.2,
          },
        },
      }),
    ]);

    expect(sections).toEqual([
      {
        kind: "stats-single",
        entry: { brand_name: "Audi", stats: expect.objectContaining({ brand_name: "Audi" }) },
      },
    ]);
  });

  it("turns a brand_not_found get_brand_stats into a status section with clickable options", () => {
    const sections = buildEvidenceSections([
      toolCall({
        tool_name: "get_brand_stats",
        result: {
          status: "brand_not_found",
          brand_name: "Toyota",
          message: "Unknown brand 'Toyota'.",
          available_brands: ["Audi", "BMW"],
        },
      }),
    ]);

    expect(sections).toHaveLength(1);
    expect(sections[0].kind).toBe("status");
    if (sections[0].kind !== "status") throw new Error("unreachable"); // narrows the type for the lines below

    const [item] = sections[0].items;
    expect(item.title).toBe('"Toyota" is not a covered brand');
    expect(item.options).toEqual(["Audi", "BMW"]);
    // onOptionClick is what wires a clicked brand button to the next chat
    // message actually sent -- this is the one bit of real logic here.
    expect(item.onOptionClick?.("BMW")).toBe("What are the stats for BMW?");
  });

  it("splits compare_brands' mixed results into stats-multi plus a status section", () => {
    // 2 ok brands (so evidence.ts takes the "stats-multi", not
    // "stats-single", branch -- a single ok result is rendered
    // differently) plus 1 unknown brand in the SAME request.
    const okEntry = (name: string) => ({
      status: "ok" as const,
      brand_name: name,
      stats: {
        brand_name: name,
        review_count: 6034,
        avg_rating: 4.465,
        median_rating: 4.75,
        rating_std: 0.783,
        avg_car_year: 2006.2,
      },
    });
    const sections = buildEvidenceSections([
      toolCall({
        tool_name: "compare_brands",
        result: {
          brands: {
            Audi: okEntry("Audi"),
            BMW: okEntry("BMW"),
            Toyota: { status: "brand_not_found", brand_name: "Toyota", available_brands: ["Audi", "BMW"] },
          },
        },
      }),
    ]);

    const statsSection = sections.find((s) => s.kind === "stats-multi");
    const statusSection = sections.find((s) => s.kind === "status");
    expect(statsSection).toBeDefined();
    expect(statusSection).toBeDefined();
    if (statsSection?.kind !== "stats-multi") throw new Error("unreachable");
    expect(statsSection.entries.map((e) => e.brand_name)).toEqual(["Audi", "BMW"]); // Toyota went to status, not here
  });

  it("turns a successful get_common_complaints into a topics section", () => {
    const sections = buildEvidenceSections([
      toolCall({
        tool_name: "get_common_complaints",
        result: {
          status: "ok",
          brand_name: "Audi",
          sentiment: "negative",
          topic_filter: null,
          items: [{ topic_label: "engine oil & warranty", topic_id: 13, count: 42, top_keywords: "oil, miles" }],
        },
      }),
    ]);

    expect(sections).toEqual([
      {
        kind: "topics",
        groups: [
          expect.objectContaining({ brand_name: "Audi", sentiment: "negative", items: expect.any(Array) }),
        ],
      },
    ]);
  });

  it("gives a topic_not_found result a follow-up question phrased for its sentiment", () => {
    const sections = buildEvidenceSections([
      toolCall({
        tool_name: "get_common_praises",
        result: {
          status: "topic_not_found",
          brand_name: "Audi",
          sentiment: "positive",
          topic_filter: "zzz",
          items: [],
          available_topics: ["interior comfort"],
        },
      }),
    ]);

    if (sections[0].kind !== "status") throw new Error("unreachable");
    const [item] = sections[0].items;
    // "praises" (positive) must phrase the follow-up as praise, not a complaint
    expect(item.onOptionClick?.("interior comfort")).toBe("What do Audi owners praise about interior comfort?");
  });

  it("collects rating trend points and de-duplicates the brand list", () => {
    const sections = buildEvidenceSections([
      toolCall({
        tool_name: "get_rating_trends",
        result: {
          status: "ok",
          points: [
            { brand_name: "Audi", car_year: 2000, avg_rating: 4.3, review_count: 262 },
            { brand_name: "Audi", car_year: 2001, avg_rating: 4.4, review_count: 418 },
          ],
        },
      }),
    ]);

    expect(sections).toEqual([
      { kind: "trend", brands: ["Audi"], points: expect.arrayContaining([expect.any(Object)]) },
    ]);
  });

  it("turns a successful search_reviews into a reviews section carrying the query", () => {
    const sections = buildEvidenceSections([
      toolCall({
        tool_name: "search_reviews",
        result: {
          status: "ok",
          query: "engine",
          matches: [
            {
              review_id: 1,
              brand_name: "Audi",
              car_year: 2010,
              date: "2010-01-01",
              rating: 4.5,
              review_text: "Great engine.",
              word_count: 2,
            },
          ],
        },
      }),
    ]);

    expect(sections).toEqual([{ kind: "reviews", query: "engine", matches: expect.any(Array) }]);
  });

  it("falls back to a generic status item for a failed, unrecognized tool call", () => {
    const sections = buildEvidenceSections([
      toolCall({ tool_name: "some_future_tool", status: "error", result: { message: "boom" } }),
    ]);

    expect(sections).toHaveLength(1);
    if (sections[0].kind !== "status") throw new Error("unreachable");
    expect(sections[0].items[0]).toMatchObject({ toolName: "some_future_tool", title: "some_future_tool failed" });
  });

  it("drops a failed, unrecognized tool call silently only if its result has no usable message", () => {
    // call.status !== "ok" with a result that ISN'T an object with a
    // "message" key -- evidence.ts's fallback body must not crash on it.
    const sections = buildEvidenceSections([toolCall({ tool_name: "weird_tool", status: "error", result: {} })]);

    if (sections[0].kind !== "status") throw new Error("unreachable");
    expect(sections[0].items[0].body).toBe("The tool call did not complete successfully.");
  });

  it("returns an empty list when there is nothing to show", () => {
    expect(buildEvidenceSections([])).toEqual([]);
  });
});

describe("evidenceTitle", () => {
  it("returns a fixed message when there are no sections", () => {
    expect(evidenceTitle([])).toBe("No evidence yet");
  });

  it("joins brand names with ' vs ' for a comparison", () => {
    const title = evidenceTitle([
      {
        kind: "stats-multi",
        entries: [
          { brand_name: "Audi", stats: {} as never },
          { brand_name: "BMW", stats: {} as never },
        ],
      },
    ]);

    expect(title).toBe("Audi vs BMW");
  });

  it("quotes the search query for a reviews section", () => {
    const title = evidenceTitle([{ kind: "reviews", query: "engine", matches: [] }]);

    expect(title).toBe('"engine"');
  });
});
