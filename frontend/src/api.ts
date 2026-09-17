import type { ChatRequest, ChatResponse, HealthResponse } from "./types";

// Vite dev server runs on :5173 (see backend/main.py's CORS allow_origins),
// the FastAPI backend on :8000 by default (backend/steps_to_run.txt).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error(`GET /health failed: ${res.status}`);
  return res.json();
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `POST /chat failed: ${res.status}`);
  }
  return res.json();
}
