# english-transfer-agent

Prototype AI English-learning transfer agent with FastAPI + LangGraph backend and React stacked-card frontend.

The MVP focuses on the core teacher-like learning loop:

Tavily online material → extract reference sentence → generate stacked micro-cards → ask Chinese transfer question → user writes English → agent evaluates like a teacher → user retries / follows up → round summary.

Long-term learning memory is intentionally removed from the MVP to keep the interaction loop simple and stable. Current storage is limited to study sessions, cards, user answers, evaluations, and round summaries. Future versions may add memory again after the core interaction loop is stable.

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

## AI providers

The backend chooses the AI provider from `AI_PROVIDER`:

- `AI_PROVIDER=mock` uses deterministic local mock responses for development.
- `AI_PROVIDER=grok` calls the xAI Chat Completions API with structured JSON outputs and validates the response against the app schemas.

For Grok mode, provide these environment variables:

```bash
AI_PROVIDER=grok
XAI_API_KEY=your_xai_api_key
XAI_MODEL=grok-4.3
```

`XAI_MODEL` is optional and defaults to `grok-4.3`. The Grok provider is used for card generation, answer evaluation, and round summaries.

## MVP status

Implemented first-priority MVP:
- mock `/agent/start`, `/agent/answer`, and `/agent/finish`
- provider abstractions (`AiProvider`, `SearchProvider`)
- mock providers plus Tavily/Grok-compatible provider selection
- LangGraph workflows for start, answer, and finish phases
- SQLite schema bootstrap for users, sessions, cards, answers, and round summaries
- mobile-first stacked card UI with Chinese prompts, answer input, teacher feedback, follow-ups, and round summary
- dynamic card rendering (1-10 cards supported)
