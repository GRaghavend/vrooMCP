import { useEffect, useRef, useState } from "react";
import { ArrowRight, ArrowUpRight, Search } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../types";
import { KNOWN_BRAND_ORDER } from "../brandColors";

const STARTER_CHIPS = [
  "What are the stats for Lexus?",
  "What do BMW owners complain about?",
  "Rating trend for Audi and Mercedes-Benz",
  "Search reviews mentioning air suspension",
];

const STEPS = [
  { key: "vrooming", title: "vrooming", desc: "Searching owner reviews and specifications…" },
  { key: "revving", title: "revving", desc: "Analyzing trends and generating insights…" },
];

interface Props {
  messages: ChatMessage[];
  thinking: boolean;
  pinnedId: string | null;
  onPin: (id: string) => void;
  onAsk: (question: string) => void;
}

export default function ChatPane({ messages, thinking, pinnedId, onPin, onAsk }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState("");
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, thinking]);

  useEffect(() => {
    if (!thinking) {
      setActiveStep(0);
      return;
    }
    const t = setTimeout(() => setActiveStep(1), 1100);
    return () => clearTimeout(t);
  }, [thinking]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    onAsk(text);
  };

  return (
    <section className="panel panel--chat">
      <div ref={scrollRef} className="chat-pane__scroll">
        {messages.length === 0 && (
          <div className="starter-row">
            {STARTER_CHIPS.map((c) => (
              <button type="button" key={c} className="starter-chip" onClick={() => onAsk(c)}>
                {c}
              </button>
            ))}
          </div>
        )}

        {messages.map((m) => (
          <div className={`msg-row ${m.role === "user" ? "msg-row--user" : "msg-row--bot"}`} key={m.id}>
            {m.role === "user" ? (
              <div className="msg-user">{m.text}</div>
            ) : (
              <div className="msg-bot">
                <div className={`msg-answer ${m.turnStatus === "error" ? "msg-error" : ""}`}>
                  <ReactMarkdown>{m.text}</ReactMarkdown>
                </div>
                {!!m.toolCalls?.length && (
                  <button
                    type="button"
                    className={`pin-btn ${pinnedId === m.id ? "pinned" : ""}`}
                    onClick={() => onPin(m.id)}
                  >
                    <ArrowUpRight />
                    {pinnedId === m.id ? "showing this turn's evidence" : "show this turn's evidence"}
                  </button>
                )}
              </div>
            )}
          </div>
        ))}

        {thinking && (
          <div className="step-feed" key={STEPS[activeStep].key}>
            <span className="step__dot step__dot--active" />
            <div className="step__body">
              <span className="step__title">{STEPS[activeStep].title}</span>
              <span className="step__desc">{STEPS[activeStep].desc}</span>
            </div>
          </div>
        )}
      </div>

      <form className="ask-bar" onSubmit={submit}>
        <Search className="ask-bar__icon" aria-hidden="true" />
        <input
          className="ask-bar__input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about a brand, a topic, a trend, or search review text…"
        />
        <button type="submit" className="ask-bar__submit" aria-label="Ask" disabled={thinking || !draft.trim()}>
          <ArrowRight />
        </button>
      </form>
      <span className="chat-pane__footnote">Covered brands · {KNOWN_BRAND_ORDER.join(" · ")}</span>
    </section>
  );
}
