import { useEffect, useMemo, useState } from "react";
import ChatPane from "./components/ChatPane";
import EvidencePane from "./components/EvidencePane";
import { checkHealth, sendChatMessage } from "./api";
import { buildEvidenceSections } from "./evidence";
import type { ChatMessage, HealthResponse } from "./types";

const INTRO_MESSAGE: ChatMessage = {
  id: "intro",
  role: "assistant",
  text:
    "Ask about a brand's stats, what owners complain about or praise on a topic, a rating " +
    "trend across model years, or search review text directly — the assistant calls tools " +
    "against the review corpus and whatever they return gets drawn on the right.",
};

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([INTRO_MESSAGE]);
  const [thinking, setThinking] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [pinnedId, setPinnedId] = useState<string | null>(null);

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

  return (
    <div className="app-shell">
      <ChatPane
        messages={messages}
        thinking={thinking}
        health={health}
        healthError={healthError}
        pinnedId={pinnedId}
        onPin={(id) => setPinnedId((cur) => (cur === id ? null : id))}
        onAsk={ask}
      />
      <EvidencePane sections={sections} activeToolName={activeToolName} onAsk={ask} />
    </div>
  );
}
