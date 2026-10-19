import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import ChatPane from "./components/ChatPane";
import EvidencePane from "./components/EvidencePane";
import Wordmark from "./components/home/Wordmark";
import { checkHealth, sendChatMessage } from "./api";
import { buildEvidenceSections } from "./evidence";
import type { ChatMessage, HealthResponse } from "./types";
import chatBackdrop from "./assets/chat-backdrop.png";
import "./pages/chat.css";

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [thinking, setThinking] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [pinnedId, setPinnedId] = useState<string | null>(null);
  const askedInitial = useRef(false);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealthError(true));
  }, []);

  const ask = async (text: string) => {
    const question = text.trim();
    if (!question || thinking) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);
    setThinking(true);
    setPinnedId(null);

    try {
      const res = await sendChatMessage({ conversation_id: conversationId, message: question });
      setConversationId(res.conversation_id);
      setHealthError(false);
      const botMsg: ChatMessage = {
        id: res.message_id,
        role: "assistant",
        text: res.answer_text,
        toolCalls: res.tool_calls,
        turnStatus: res.status,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setHealthError(true);
      const botMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: err instanceof Error ? err.message : "Could not reach the backend.",
        turnStatus: "error",
      };
      setMessages((prev) => [...prev, botMsg]);
    } finally {
      setThinking(false);
    }
  };

  // A query typed on the homepage arrives as `/chat?q=...` — fire it once on arrival.
  useEffect(() => {
    if (askedInitial.current) return;
    askedInitial.current = true;
    const q = new URLSearchParams(window.location.search).get("q");
    if (q && q.trim()) ask(q.trim());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeMessage = useMemo(() => {
    if (pinnedId) {
      const pinned = messages.find((m) => m.id === pinnedId);
      if (pinned) return pinned;
    }
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].toolCalls?.length) return messages[i];
    }
    return null;
  }, [messages, pinnedId]);

  const sections = useMemo(
    () => (activeMessage?.toolCalls ? buildEvidenceSections(activeMessage.toolCalls) : []),
    [activeMessage]
  );

  const activeToolName = useMemo(() => {
    const names = Array.from(new Set(activeMessage?.toolCalls?.map((c) => c.tool_name) ?? []));
    return names.length ? names.join(", ") : null;
  }, [activeMessage]);

  let statusLabel = "connecting";
  let statusClass = "";
  if (healthError) {
    statusLabel = "backend unavailable";
    statusClass = "down";
  } else if (health) {
    statusLabel = health.mcp_connected ? `${health.tool_count} tools connected` : "mcp disconnected";
    statusClass = health.mcp_connected ? "ok" : "down";
  }

  return (
    <div className="chat-app">
      <div className="chat-app__backdrop" style={{ "--chat-bg": `url(${chatBackdrop})` } as CSSProperties} />

      <header className="chat-app__header">
        <Wordmark />
        <span className="chat-app__divider" aria-hidden="true" />
        <h1 className="chat-app__headline">
          Ask. Compare. <span className="chat-app__headline-gold">Choose Smarter.</span>
        </h1>
        <span className="chat-app__status">
          <span className={`chat-app__status-dot ${statusClass}`} />
          {statusLabel}
        </span>
      </header>

      <div className="chat-app__panels">
        <ChatPane messages={messages} thinking={thinking} pinnedId={pinnedId} onPin={(id) => setPinnedId((cur) => (cur === id ? null : id))} onAsk={ask} />
        <EvidencePane sections={sections} activeToolName={activeToolName} onAsk={ask} />
      </div>
    </div>
  );
}
