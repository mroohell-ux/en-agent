from __future__ import annotations

import uuid

from fastapi import HTTPException

from app.schemas import AnswerEvaluation, AnswerRequest, FinishRequest, LearningCard, RoundSummary, StartRequest, StartResponse
from app.workflow.graph import WorkflowDeps, build_answer_graph, build_finish_graph, build_start_graph


class AgentService:
    def __init__(self, ai_provider, search_provider) -> None:
        deps = WorkflowDeps(ai_provider=ai_provider, search_provider=search_provider)
        self.start_graph = build_start_graph(deps)
        self.answer_graph = build_answer_graph(deps)
        self.finish_graph = build_finish_graph(deps)

    def start(self, req: StartRequest) -> StartResponse:
        session_id = str(uuid.uuid4())
        state = self.start_graph.invoke(
            {
                "mode": "start",
                "user_id": req.userId,
                "session_id": session_id,
                "topic": req.topic,
                "level": req.level,
            }
        )
        cards = [LearningCard(**c) for c in state.get("cards", [])]
        if not cards:
            raise HTTPException(status_code=400, detail="No cards returned from workflow")
        return StartResponse(sessionId=session_id, cards=cards)

    def answer(self, req: AnswerRequest) -> AnswerEvaluation:
        state = self.answer_graph.invoke(
            {
                "mode": "answer",
                "session_id": req.sessionId,
                "card_id": req.cardId,
                "user_answer": req.userAnswer,
                "attempt_number": req.attemptNumber,
            }
        )
        return AnswerEvaluation(**state["evaluation"])

    def finish(self, req: FinishRequest) -> RoundSummary:
        state = self.finish_graph.invoke({"mode": "finish", "session_id": req.sessionId})
        return RoundSummary(**state["round_summary"])
