# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload          # dev server on :8000
```

### Frontend (SvelteKit)
```bash
cd frontend
npm install
npm run dev                        # dev server on :5173
npm run build                      # static build → frontend/build/
npm run check                      # svelte-check type checking
```

### Docker (Backend)
```bash
cd backend
docker build -t deepresearch-backend .
docker run -p 8000:8000 --env-file .env deepresearch-backend
```

### Environment
Copy `.env.example` to `backend/.env`. Required keys: `OPENAI_API_KEY`, `FIRECRAWL_API_KEY`. If `AZURE_STORAGE_CONNECTION_STRING` is empty, reports are saved locally to `backend/local_reports/`.

## Architecture

**Two-process app**: FastAPI backend + SvelteKit SPA frontend (adapter-static). Frontend communicates via REST + SSE (Server-Sent Events). No LangChain — uses OpenAI SDK directly.

### Backend Flow
The research engine (`services/research_engine.py`) orchestrates a loop:
1. **Query decomposition** → GPT-4o splits query into sub-queries (response_format: json_object)
2. **Parallel search** → Firecrawl via `sources/web_source.py`, top 5 pages scraped for full content
3. **Analysis** → GPT-4o decides if more research needed; loops back to step 2 (max `MAX_RESEARCH_DEPTH` rounds, default 3)
4. **Report generation** → GPT-4o produces Markdown report
5. **Storage** → Azure Blob Storage (or local file fallback)

Each step emits `ProgressEvent` via `TaskRegistry.emit()` → pushed to `asyncio.Queue` subscribers → streamed as SSE.

### Key Backend Components
- **`services/task_registry.py`** — Singleton in-memory registry. `TaskInfo` tracks status/progress/messages. `subscribe()` returns AsyncGenerator for SSE. Multiple SSE clients supported per task via separate queues.
- **`sources/base.py`** — Abstract `ResearchSource` with `search()` and `fetch_content()`. Extend this to add RDB/SearchDB sources.
- **`services/research_engine.py`** — Module-level semaphores (`MAX_CONCURRENT_LLM_CALLS=10`, `MAX_CONCURRENT_SEARCH_CALLS=10`) gate all external API calls across all tasks. JSON responses parsed via `_parse_json()` which strips markdown code blocks.
- **`services/blob_storage.py`** — Azure Blob async client (requires `aiohttp`). Falls back to local file writes when connection string is empty.

### Frontend State
- **Svelte 5 runes** (`$state`, `$effect`) in page components; writable stores for cross-component state
- **`stores/chat.ts`** — `ChatSession[]` persisted to localStorage (title, task_id, messages, status, result_url)
- **`stores/research.ts`** — Active task progress/steps for the progress UI
- **`api.ts`** — `startResearch()`, `getTaskStatus()`, `subscribeToTask()` (EventSource wrapper), `cancelResearch()`
- **Reconnection**: On page load, checks localStorage for running tasks → `GET /research/{id}` → re-subscribes SSE if still running

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/research` | Start task → `{ task_id }` |
| GET | `/research/{task_id}` | Poll status/result |
| GET | `/research/{task_id}/stream` | SSE progress stream |
| POST | `/research/{task_id}/cancel` | Cancel task |
| GET | `/health` | Health check |

### Progress Values
`0-5` query analysis → `10-40` search (increments per sub-query/round) → `50` analysis → `80` report generation → `90` saving → `100` complete

## Conventions
- Backend uses absolute imports from the `backend/` directory root (e.g., `from services.task_registry import ...`)
- All OpenAI calls requiring JSON use `response_format={"type": "json_object"}` with `_parse_json()` fallback
- SSE events: `{"event_type": "progress"|"completed"|"failed", "message": str, "progress": int, "data": any}`
- Frontend API base URL configurable via `VITE_API_BASE_URL` env var (defaults to `http://localhost:8000`)
- No test suite exists yet
