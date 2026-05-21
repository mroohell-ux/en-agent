from __future__ import annotations

import json
import uuid

from fastapi import HTTPException

from app.db.memory_store import get_conn, get_memory, save_known
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
                "retry_count": 0,
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
            }
        )
        return AnswerEvaluation(**state["evaluation"])

    def finish(self, req: FinishRequest) -> RoundSummary:
        state = self.finish_graph.invoke({"mode": "finish", "session_id": req.sessionId})
        return RoundSummary(**state["round_summary"])

    def mark_known(self, card_id: str):
        conn = get_conn()
        cur = conn.cursor()
        row = cur.execute(
            "SELECT c.card_json,c.id,s.user_id FROM cards c JOIN sessions s ON c.session_id=s.id WHERE c.id=?",
            (card_id,),
        ).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Card not found")

        card = json.loads(row["card_json"])
        save_known(row["user_id"], "PATTERN", card.get("target", ""), row["id"])
        if card.get("extractedFromOriginal"):
            save_known(row["user_id"], "CHUNK", card["extractedFromOriginal"], row["id"])
        return {"ok": True}

    def read_memory(self, user_id: str = "default-user"):
        return get_memory(user_id)
