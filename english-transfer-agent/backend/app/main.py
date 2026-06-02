from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.db.store import init_db
from app.providers.ai import build_ai_provider
from app.providers.search import build_search_provider
from app.schemas import AnswerRequest, FinishRequest, StartRequest
from app.services.agent_service import AgentService

load_dotenv()

app = FastAPI(title="english-transfer-agent")
search_provider = build_search_provider(os.getenv("SEARCH_PROVIDER", "mock"))
ai_provider = build_ai_provider(os.getenv("AI_PROVIDER", "mock"))
agent_service = AgentService(ai_provider=ai_provider, search_provider=search_provider)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/agent/start")
def start_agent(req: StartRequest):
    return agent_service.start(req)


@app.post("/agent/answer")
def answer_agent(req: AnswerRequest):
    return agent_service.answer(req)


@app.post("/agent/finish")
def finish_agent(req: FinishRequest):
    return agent_service.finish(req)
