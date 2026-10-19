/**
 * Tests for api.ts -- the two functions that call the FastAPI backend
 * over HTTP (fetch).
 *
 * We never want a real backend running for these: instead we replace
 * `global.fetch` with a fake function (vi.fn()) that we fully control,
 * the same idea as Python's unittest.mock, just vitest's version of it.
 *
 * Run with:
 *   npm test                 (from frontend/)
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { checkHealth, sendChatMessage } from "./api";

afterEach(() => {
  vi.unstubAllGlobals(); // undo the fetch replacement after each test
});

function fakeResponse(body: unknown, ok: boolean, status = 200) {
  return { ok, status, json: async () => body } as Response;
}

describe("checkHealth", () => {
  it("parses a successful /health response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(fakeResponse({ status: "ok", mcp_connected: true, tool_count: 6 }, true)),
    );

    const result = await checkHealth();

    expect(result).toEqual({ status: "ok", mcp_connected: true, tool_count: 6 });
    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/health");
  });

  it("throws, including the status code, when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(fakeResponse({}, false, 503)));

    await expect(checkHealth()).rejects.toThrow("GET /health failed: 503");
  });
});

describe("sendChatMessage", () => {
  it("posts the request body and returns the parsed chat response", async () => {
    const fakeFetch = vi.fn().mockResolvedValue(
      fakeResponse(
        { conversation_id: "c1", message_id: "m1", answer_text: "Hi!", tool_calls: [], status: "ok" },
        true,
      ),
    );
    vi.stubGlobal("fetch", fakeFetch);

    const result = await sendChatMessage({ message: "hello" });

    expect(result.answer_text).toBe("Hi!");
    // Checks we actually send JSON, not that fetch just got called --
    // a frontend sending the wrong content-type is a real, silent bug.
    const [, options] = fakeFetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(options.body)).toEqual({ message: "hello" });
  });

  it("raises the backend's own `detail` message when the request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(fakeResponse({ detail: "MCP tool server is not connected" }, false, 503)),
    );

    await expect(sendChatMessage({ message: "hello" })).rejects.toThrow("MCP tool server is not connected");
  });

  it("falls back to a generic status-code message when the error body isn't JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new SyntaxError("not json");
        },
      } as unknown as Response),
    );

    await expect(sendChatMessage({ message: "hello" })).rejects.toThrow("POST /chat failed: 500");
  });
});
