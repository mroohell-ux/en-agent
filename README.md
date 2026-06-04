# english-transfer-agent

An article-based English speaking teacher agent. It turns one article into speaking practice: retell the main idea, answer teacher questions, learn useful expressions, get corrected, repeat better versions, and review mistakes.

The product principle is:

> The article is only the source material. The user’s output is the center.

Default flow: **Read → Speak → Correct → Repeat → Reuse → Review**.

## Project structure

```text
english-transfer-agent/
  backend/   FastAPI + LangGraph + SQLite
  frontend/  React article lesson workspace
```

## What changed

The original MVP generated generic micro-cards from online material. The refactored app builds one speaking-first lesson from one article URL or pasted article text.

A lesson includes:

- article source metadata and raw text
- main idea and key points
- a main-idea retell task
- article-based teacher questions
- 5–10 reusable expressions, vocabulary items, grammar points, and sentence patterns
- optional IELTS-style tasks based on the same article
- speaking corrections, reviewable mistakes, and lesson summaries

The old endpoints remain available:

- `POST /agent/start`
- `POST /agent/answer`
- `POST /agent/finish`

## Backend setup

```bash
cd english-transfer-agent/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The backend defaults to deterministic mock providers, so it runs locally without real AI keys.

## Frontend setup

```bash
cd english-transfer-agent/frontend
npm install
npm run dev
```

Open the Vite URL and paste an article. The default sample text is about JD Vance’s “childless cat ladies” comment and demonstrates expressions such as:

- `unleash fury`
- `did not land well`
- `take issue with`
- `have a direct stake in`

## New API endpoints

### Create a speaking-first lesson from an article

```bash
curl -X POST http://localhost:8000/lessons/from-article \
  -H 'Content-Type: application/json' \
  -d '{
    "userId": "default-user",
    "level": "B2-C1",
    "articleText": "JD Vance’s old childless cat ladies comment unleashed fury...",
    "mode": "speaking_first",
    "includeIelts": true
  }'
```

Returns an `ArticleLesson` with:

- `mainIdea`
- `keyPoints`
- `retellTask`
- `questions`
- `usefulLanguage`
- optional `ieltsTasks`
- `progress`

### Submit the main-idea retell

```bash
curl -X POST http://localhost:8000/lessons/{lessonId}/retell \
  -H 'Content-Type: application/json' \
  -d '{
    "transcript": "The article is about people angry about a comment because it is sexist.",
    "attemptNumber": 1
  }'
```

Returns `TeacherCorrection`, including a score, natural version, advanced version, mistakes, key improvements, and a repeat prompt.

### Answer an article question

```bash
curl -X POST http://localhost:8000/lessons/{lessonId}/questions/{questionId}/answer \
  -H 'Content-Type: application/json' \
  -d '{
    "transcript": "Many people took issue with the phrase because it reduced women to family status.",
    "attemptNumber": 1
  }'
```

### Reuse useful language from the article

```bash
curl -X POST http://localhost:8000/lessons/{lessonId}/useful-language/{itemId}/practice \
  -H 'Content-Type: application/json' \
  -d '{
    "transcript": "The product update did not land well with users.",
    "attemptNumber": 1
  }'
```

### Finish and review a lesson

```bash
curl -X POST http://localhost:8000/lessons/{lessonId}/finish
```

Returns a summary with:

- what the user did well
- repeated mistakes
- useful expressions learned
- suggested next practice

## AI providers

`AI_PROVIDER=mock` returns deterministic article lesson data and speaking corrections for development. Existing OpenAI-compatible providers are still behind the `AiProvider` abstraction; future providers can be added without hardcoding the product to one vendor.

Supported environment values include:

- `AI_PROVIDER=mock`
- `AI_PROVIDER=grok`
- `AI_PROVIDER=alibaba` / `dashscope` / `qwen`

## Storage

SQLite bootstrap now keeps old tables and adds article lesson tables:

- `article_lessons`
- `article_sources`
- `teacher_questions`
- `useful_language_items`
- `speaking_answers`
- `teacher_corrections`
- `lesson_mistakes`
- `lesson_summaries`

## Testing

Frontend build:

```bash
cd english-transfer-agent/frontend
npm run build
```

Backend tests are in `english-transfer-agent/backend/tests`. Run them after installing backend dependencies:

```bash
cd english-transfer-agent/backend
PYTHONPATH=. pytest -q
```
