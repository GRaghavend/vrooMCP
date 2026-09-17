import { useEffect, useRef, useState } from "react";
import type { ChatMessage, HealthResponse } from "../types";
import { KNOWN_BRAND_ORDER } from "../brandColors";

const STARTER_CHIPS = [
  "What are the stats for Lexus?",
  "What do BMW owners complain about?",
  "Rating trend for Audi and Mercedes-Benz",
  "Search reviews mentioning air suspension",
];

interface Props {
  messages: ChatMessage[];
  thinking: boolean;
  health: HealthResponse | null;
  healthError: boolean;
  pinnedId: string | null;
  onPin: (id: string) => void;
  onAsk: (question: string) => void;
}

export default function ChatPane({ messages, thinking, health, healthError, pinnedId, onPin, onAsk }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, thinking]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    onAsk(text);
  };

  let healthLabel = "connecting…";
  let healthClass = "";
  if (healthError) {
    healthLabel = "backend unavailable";
    healthClass = "down";
  } else if (health) {
    healthLabel = health.mcp_connected ? `${health.tool_count} tools connected` : "mcp disconnected";
    healthClass = health.mcp_connected ? "ok" : "down";
  }

  return (
    <section className="chat-pane">
      <header className="chat-header">
        <div className="chat-header-left">
          <span className="chat-logo" />
          <span className="chat-title">vrooMCP</span>
          <span className="pill mono">owner-review corpus</span>
        </div>
        <span className={`health-label mono ${healthClass}`}>{healthLabel}</span>
      </header>

      <div ref={scrollRef} className="chat-scroll">
        {messages.map((m) => (
          <div className="msg-row" key={m.id}>
            {m.role === "user" ? (
              <div className="msg-user">{m.text}</div>
            ) : (
              <div className="msg-bot">
                {!!m.toolCalls?.length && (
                  <div className="tool-calls-row">
                    {m.toolCalls.map((c, i) => (
                      <span className="tool-call-pill mono" key={i}>
                        <span
                          className="tool-call-dot"
                          style={{ background: c.status === "ok" ? "var(--pos)" : "var(--neg)" }}
                        />
                        {c.tool_name}({Object.entries(c.arguments).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})
                      </span>
                    ))}
                  </div>
                )}
                <p className={`msg-answer ${m.turnStatus === "error" ? "msg-error" : ""}`}>{m.text}</p>
                {!!m.toolCalls?.length && (
                  <button
                    type="button"
                    className={`pin-btn mono ${pinnedId === m.id ? "pinned" : ""}`}
                    onClick={() => onPin(m.id)}
                  >
                    {pinnedId === m.id ? "showing this turn's evidence" : "show this turn's evidence"}
                  </button>
                )}
                {m.id === messages[0]?.id && (
                  <div className="chips-row">
                    {STARTER_CHIPS.map((c) => (
                      <button type="button" key={c} className="chip" onClick={() => onAsk(c)}>
                        {c}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {thinking && <span className="thinking-label mono">calling tools…</span>}
      </div>

      <form className="chat-form" onSubmit={submit}>
        <div className="chat-input-row">
          <input
            className="chat-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about a brand, a topic, a trend, or search review text…"
          />
          <button type="submit" className="send-btn" disabled={thinking || !draft.trim()}>
            Send
          </button>
        </div>
        <span className="chat-footnote mono">Covered brands: {KNOWN_BRAND_ORDER.join(" · ")}</span>
      </form>
    </section>
  );
}
