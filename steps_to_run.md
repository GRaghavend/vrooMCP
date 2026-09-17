# Steps to run

Run from the repo root: `/Users/raghavender/Python For Jupyter/car_brand_reviews`

## 1. Backend (FastAPI + MCP + Ollama)

```bash
source .venv_mcp/bin/activate
ollama pull qwen2.5:7b-instruct    # one-time, only if not already pulled
ollama serve &                     # if Ollama isn't already running in the background
uvicorn backend.main:app --reload
```

## 2. Frontend (Vite dev server)

```bash
cd frontend
npm install       # first time only, or after package.json changes
npm run dev
```

## Ports

| Port | What |
|---|---|
| 8000 | FastAPI backend (`uvicorn backend.main:app --reload` default) |
| 11434 | Ollama server (`ollama serve` default) |
| 5173 | Vite dev server (frontend) — allowed CORS origin in `backend/main.py` |
