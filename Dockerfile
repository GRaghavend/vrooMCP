# Backend image for vrooMCP: FastAPI (backend/) + the MCP server it spawns
# as a subprocess (mcp_server/). The frontend is not part of this image --
# see frontend/README.md for running it separately (it's a static Vite app
# with its own, much simpler, build).
#
# Build context must be the repo root (not backend/), because backend/main.py
# expects mcp_server/ as a sibling directory on sys.path, exactly like it
# does when run locally -- see backend/main.py's own sys.path.insert() call.
#
# Ollama is NOT containerized here. It's a large, separately-managed model
# runtime (multi-GB weights) that most people already run on the host --
# baking it into this image would bloat it for no benefit. Point this
# container at a host-run Ollama via the OLLAMA_HOST env var (see
# docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app
# The work directory should be app - you need to use the build command
# from the app directory then only will, the backend and mcp server
# be recognized.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY mcp_server/ mcp_server/
COPY data/processed/ data/processed/

EXPOSE 8000

# Run from /app (= repo root inside the image) so backend/main.py's
# sys.path setup resolves mcp_server/ the same way it does locally.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
