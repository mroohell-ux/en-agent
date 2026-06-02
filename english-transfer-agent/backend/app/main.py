from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.store import init_db
from app.providers.ai import build_ai_provider
from app.providers.search import build_search_provider
from app.schemas import AnswerRequest, FinishRequest, StartRequest
from app.services.agent_service import AgentService

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


def _get_cors_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


app = FastAPI(title="english-transfer-agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_provider = build_search_provider(os.getenv("SEARCH_PROVIDER", "mock"))
ai_provider = build_ai_provider(os.getenv("AI_PROVIDER", "mock"))
agent_service = AgentService(ai_provider=ai_provider, search_provider=search_provider)


@app.on_event("startup")
def startup() -> None:
    init_db()
    logger.info("Backend startup complete with AI_PROVIDER=%s SEARCH_PROVIDER=%s", os.getenv("AI_PROVIDER", "mock"), os.getenv("SEARCH_PROVIDER", "mock"))


@app.post("/agent/start")
def start_agent(req: StartRequest):
    logger.info("POST /agent/start topic=%s level=%s user=%s", req.topic, req.level, req.userId)
    return agent_service.start(req)


@app.post("/agent/answer")
def answer_agent(req: AnswerRequest):
    logger.info("POST /agent/answer session=%s card=%s attempt=%s", req.sessionId, req.cardId, req.attemptNumber)
    return agent_service.answer(req)


@app.post("/agent/finish")
def finish_agent(req: FinishRequest):
    logger.info("POST /agent/finish session=%s", req.sessionId)
    return agent_service.finish(req)
