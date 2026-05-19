# english-transfer-agent

Prototype AI English-learning transfer agent with FastAPI + LangGraph backend and React stacked-card frontend.

## Project structure

```
english-transfer-agent/
  backend/
  frontend/
```

## Backend setup

```bash
cd english-transfer-agent/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Frontend setup

```bash
cd english-transfer-agent/frontend
npm install
npm run dev
```

## MVP status

Implemented first-priority MVP:
- mock `/agent/start`, `/agent/answer`, `/agent/finish`, `/cards/{cardId}/mark-known`, `/memory`
- provider abstractions (`AiProvider`, `SearchProvider`)
- mock providers + Tavily/Grok stubs
- LangGraph workflow skeleton with required node names
- SQLite schema bootstrap for memory tables
- mobile-first stacked card UI (no dashboard/chat wall)
- dynamic card rendering (1-10+ supported)
