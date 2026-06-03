from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException

from app.logging_utils import color_request_log
from app.schemas import AnswerEvaluation, AnswerRequest, FinishRequest, LearningCard, RoundSummary, SearchResult, StartRequest, StartResponse
from app.workflow.graph import WorkflowDeps, build_answer_graph, build_finish_graph, build_start_graph


logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self, ai_provider, search_provider) -> None:
        deps = WorkflowDeps(ai_provider=ai_provider, search_provider=search_provider)
        self.start_graph = build_start_graph(deps)
        self.answer_graph = build_answer_graph(deps)
        self.finish_graph = build_finish_graph(deps)

    def start(self, req: StartRequest) -> StartResponse:
        session_id = str(uuid.uuid4())
        graph_payload = {
            "mode": "start",
            "user_id": req.userId,
            "session_id": session_id,
            "topic": req.topic,
            "level": req.level,
        }
        logger.debug(color_request_log("Invoking start workflow payload=%s"), graph_payload)
        state = self.start_graph.invoke(graph_payload)
        logger.debug("Start workflow returned keys=%s cards_count=%s", sorted(state.keys()), len(state.get("cards", [])))
        cards = [LearningCard(**c) for c in state.get("cards", [])]
        if not cards:
            raise HTTPException(status_code=400, detail="No cards returned from workflow")
        source_articles = [SearchResult(**result) for result in state.get("search_results", [])]
        return StartResponse(sessionId=session_id, cards=cards, sourceArticles=source_articles)

    def answer(self, req: AnswerRequest) -> AnswerEvaluation:
        graph_payload = {
            "mode": "answer",
            "session_id": req.sessionId,
            "card_id": req.cardId,
            "user_answer": req.userAnswer,
            "attempt_number": req.attemptNumber,
        }
        logger.debug(color_request_log("Invoking answer workflow payload=%s"), graph_payload)
        state = self.answer_graph.invoke(graph_payload)
        logger.debug("Answer workflow evaluation payload=%s", state.get("evaluation"))
        return AnswerEvaluation(**state["evaluation"])

    def finish(self, req: FinishRequest) -> RoundSummary:
        graph_payload = {"mode": "finish", "session_id": req.sessionId}
        logger.debug(color_request_log("Invoking finish workflow payload=%s"), graph_payload)
        state = self.finish_graph.invoke(graph_payload)
        logger.debug("Finish workflow round_summary payload=%s", state.get("round_summary"))
        return RoundSummary(**state["round_summary"])
