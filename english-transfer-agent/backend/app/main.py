from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.store import init_db
from app.logging_utils import color_request_log
from app.providers.ai import build_ai_provider
from app.providers.search import build_search_provider
from app.schemas import AnswerRequest, FinishRequest, StartRequest
from app.services.agent_service import AgentService

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logging.getLogger("httpx").setLevel(os.getenv("HTTPX_LOG_LEVEL", "WARNING").upper())
logging.getLogger("httpcore").setLevel(os.getenv("HTTPCORE_LOG_LEVEL", "WARNING").upper())
logger = logging.getLogger(__name__)


def _request_payload(req: Any) -> dict[str, Any]:
    if hasattr(req, "model_dump"):
        return req.model_dump()
    return dict(req)


def _log_api_request(path: str, req: Any) -> None:
    payload = _request_payload(req)
    logger.info(color_request_log("POST %s -> AgentService payload=%s"), path, payload)
    logger.debug(color_request_log("POST %s request payload detail=%s"), path, payload)


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
    _log_api_request("/agent/start", req)
    return agent_service.start(req)


@app.post("/agent/answer")
def answer_agent(req: AnswerRequest):
    _log_api_request("/agent/answer", req)
    return agent_service.answer(req)


@app.post("/agent/finish")
def finish_agent(req: FinishRequest):
    _log_api_request("/agent/finish", req)
    return agent_service.finish(req)
