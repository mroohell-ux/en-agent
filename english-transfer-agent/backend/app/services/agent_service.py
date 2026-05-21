from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import HTTPException

from app.db.memory_store import get_conn, get_memory, save_known, save_review, save_weak_item
from app.prompts.card_generation import build_card_generation_prompt
from app.prompts.evaluation import build_evaluation_prompt
from app.prompts.round_summary import build_round_summary_prompt
from app.schemas import AnswerRequest, FinishRequest, LearningCard, StartRequest, StartResponse


class AgentService:
    def __init__(self, ai_provider, search_provider) -> None:
        self.ai_provider = ai_provider
        self.search_provider = search_provider

    def start(self, req: StartRequest) -> StartResponse:
        session_id = str(uuid.uuid4())
        memory = get_memory(req.userId)
        query = self._build_search_query(req.topic, req.level, memory)
        search_results = self.search_provider.search(query, max_results=5)
        prompt = build_card_generation_prompt(
            req.topic,
            req.level,
            [r.model_dump() for r in search_results],
            memory,
        )
        card_set = self.ai_provider.generate_cards(prompt)

        known_targets = {k.lower().strip() for k in memory.get("knownPatterns", []) + memory.get("knownChunks", [])}
        filtered: list[LearningCard] = []
        for card in card_set.cards:
            if len(filtered) >= 10:
                break
            if not card.target.strip() or not card.chinesePrompt.strip():
                continue
            if card.target.lower().strip() in known_targets:
                continue
            filtered.append(card)

        if not filtered:
            raise HTTPException(status_code=400, detail="No valid cards generated")

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (req.userId,))
        cur.execute(
            "INSERT INTO sessions (id,user_id,topic,created_at) VALUES (?,?,?,?)",
            (session_id, req.userId, req.topic, datetime.utcnow().isoformat()),
        )
        for card in filtered:
            cur.execute(
                "INSERT INTO cards (id,session_id,target,type,topic,card_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    card.id,
                    session_id,
                    card.target,
                    card.type,
                    req.topic,
                    card.model_dump_json(),
                    datetime.utcnow().isoformat(),
                ),
            )
        conn.commit()
        conn.close()
        return StartResponse(sessionId=session_id, cards=filtered)

    def answer(self, req: AnswerRequest):
        conn = get_conn()
        cur = conn.cursor()
        session = cur.execute("SELECT * FROM sessions WHERE id=?", (req.sessionId,)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        card_row = cur.execute("SELECT * FROM cards WHERE id=? AND session_id=?", (req.cardId, req.sessionId)).fetchone()
        if not card_row:
            raise HTTPException(status_code=404, detail="Card not found")

        card = json.loads(card_row["card_json"])
        prompt = build_evaluation_prompt(card, req.userAnswer)
        evaluation = self.ai_provider.evaluate_answer(prompt)

        cur.execute(
            "INSERT INTO answers (session_id,card_id,user_answer,score,evaluation_json,created_at) VALUES (?,?,?,?,?,?)",
            (
                req.sessionId,
                req.cardId,
                req.userAnswer,
                evaluation.score,
                evaluation.model_dump_json(),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        self._apply_memory_decision(session["user_id"], req.cardId, card, evaluation.model_dump())
        return evaluation

    def finish(self, req: FinishRequest):
        conn = get_conn()
        cur = conn.cursor()
        session = cur.execute("SELECT * FROM sessions WHERE id=?", (req.sessionId,)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        card_rows = cur.execute("SELECT card_json FROM cards WHERE session_id=?", (req.sessionId,)).fetchall()
        answer_rows = cur.execute("SELECT card_id,user_answer,score,evaluation_json FROM answers WHERE session_id=?", (req.sessionId,)).fetchall()

        cards = [json.loads(r["card_json"]) for r in card_rows]
        answers = []
        for r in answer_rows:
            evaluation = json.loads(r["evaluation_json"]) if r["evaluation_json"] else {}
            answers.append({
                "cardId": r["card_id"],
                "userAnswer": r["user_answer"],
                "score": r["score"],
                "evaluation": evaluation,
                "mistakes": evaluation.get("mistakes", []),
            })

        round_data = {
            "session": dict(session),
            "cards": cards,
            "answers": answers,
            "scores": [a.get("score", 0) for a in answers],
            "mistakes": [m for a in answers for m in a.get("mistakes", [])],
        }

        prompt = build_round_summary_prompt(round_data)
        summary = self.ai_provider.summarize_round(prompt)

        cur.execute(
            "INSERT INTO round_summaries (session_id,summary_json,created_at) VALUES (?,?,?)",
            (req.sessionId, summary.model_dump_json(), datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()

        for item in summary.reviewPlan:
            save_review(session["user_id"], item.type.upper(), item.item, f"Review: {item.item}", days=item.reviewAfterDays)
        return summary

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

    def _apply_memory_decision(self, user_id: str, card_id: str, card: dict, evaluation: dict) -> None:
        decision = evaluation.get("memoryDecision", {})
        action = decision.get("action", "none")
        target = card.get("target", "")
        if action == "mark_known":
            save_known(user_id, "PATTERN", target, card_id)
        elif action == "save_for_review":
            save_review(user_id, "PATTERN", target, f"Practice: {target}")
            for m in evaluation.get("mistakes", []):
                save_weak_item(
                    user_id,
                    m.get("type", "GRAMMAR").upper(),
                    m.get("reviewItem", target),
                    m.get("original", ""),
                    m.get("correction", ""),
                    m.get("explanationChinese", ""),
                    "medium",
                )
        elif action == "save_as_weak":
            save_weak_item(user_id, "PATTERN", target, "target not transferred", target, "未迁移目标表达", "high")

    def _build_search_query(self, topic: str, level: str, memory: dict) -> str:
        avoid = ", ".join(memory.get("knownTopics", [])[:3] + memory.get("knownPatterns", [])[:3])
        prefer = ", ".join(memory.get("weakGrammarPoints", [])[:3] + memory.get("weakPatterns", [])[:3])
        return (
            f"well-written English article for {level}, topic {topic}, short to medium, "
            f"avoid political and too technical, avoid: {avoid or 'none'}, "
            f"prefer naturally containing: {prefer or 'none'}"
        )
