from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from app.db.store import get_conn
from app.prompts.card_generation import build_card_generation_prompt
from app.prompts.evaluation import build_evaluation_prompt
from app.prompts.round_summary import build_round_summary_prompt

logger = logging.getLogger(__name__)

REQUIRED_CARD_FIELDS = {
    "id",
    "type",
    "originalReference",
    "extractedFromOriginal",
    "target",
    "referenceExample",
    "chinesePrompt",
    "expectedAnswer",
    "mustContain",
}


def build_search_query(state, deps):
    query = (
        f"well-written English article for {state['level']}, topic {state['topic']}, short to medium, "
        "useful for English transfer practice, avoid political and too technical content"
    )
    return {"search_query": query}


def search_material_with_tavily(state, deps):
    results = deps.search_provider.search(state["search_query"], max_results=5)
    search_results = [r.model_dump() for r in results]
    dump_path = _dump_search_material(state, search_results)
    logger.info("Saved raw search material to %s", dump_path)
    return {"search_results": search_results, "search_dump_path": str(dump_path)}


def generate_learning_cards(state, deps):
    prompt = build_card_generation_prompt(
        topic=state["topic"],
        level=state["level"],
        search_results=state.get("search_results", []),
    )
    card_set = deps.ai_provider.generate_cards(prompt)
    return {"cards": [c.model_dump() for c in card_set.cards]}


def validate_cards(state, deps):
    valid_cards: list[dict] = []
    for card in state.get("cards", []):
        if len(valid_cards) >= 10:
            break
        if not REQUIRED_CARD_FIELDS.issubset(card.keys()):
            continue
        if not str(card.get("target", "")).strip() or not str(card.get("chinesePrompt", "")).strip():
            continue
        valid_cards.append(card)
    if not valid_cards:
        raise HTTPException(status_code=400, detail="No valid cards generated")
    return {"filtered_cards": valid_cards}


def save_session_and_cards(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (state["user_id"],))
    cur.execute(
        "INSERT INTO sessions (id,user_id,topic,created_at) VALUES (?,?,?,?)",
        (state["session_id"], state["user_id"], state["topic"], datetime.utcnow().isoformat()),
    )
    saved_cards = []
    for card in state.get("filtered_cards", []):
        card_to_save = dict(card)
        existing = cur.execute("SELECT id FROM cards WHERE id=?", (card_to_save["id"],)).fetchone()
        if existing:
            card_to_save["id"] = f"{state['session_id']}-{card_to_save['id']}"
        cur.execute(
            "INSERT INTO cards (id,session_id,target,type,topic,card_json,created_at) VALUES (?,?,?,?,?,?,?)",
            (
                card_to_save["id"],
                state["session_id"],
                card_to_save["target"],
                card_to_save["type"],
                state["topic"],
                json.dumps(card_to_save, ensure_ascii=False),
                datetime.utcnow().isoformat(),
            ),
        )
        saved_cards.append(card_to_save)
    conn.commit()
    conn.close()
    return {"cards": saved_cards, "filtered_cards": saved_cards}


def load_session_and_card(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    session = cur.execute("SELECT * FROM sessions WHERE id=?", (state["session_id"],)).fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    card_row = cur.execute("SELECT * FROM cards WHERE id=? AND session_id=?", (state["card_id"], state["session_id"])).fetchone()
    card_ids = [r["id"] for r in cur.execute("SELECT id FROM cards WHERE session_id=? ORDER BY created_at,id", (state["session_id"],)).fetchall()]
    conn.close()
    if not card_row:
        raise HTTPException(status_code=404, detail="Card not found")
    is_last_card = bool(card_ids) and card_ids[-1] == state["card_id"]
    return {"current_card": json.loads(card_row["card_json"]), "user_id": session["user_id"], "is_last_card": is_last_card}


def evaluate_answer(state, deps):
    prompt = build_evaluation_prompt(state["current_card"], state["user_answer"])
    evaluation = deps.ai_provider.evaluate_answer(prompt).model_dump()
    if state.get("is_last_card") and evaluation.get("targetUsed") and int(evaluation.get("score", 0) or 0) >= 80:
        evaluation["nextAction"] = "finish_round"
        evaluation["followUpPromptChinese"] = None
        evaluation["teacherResponseChinese"] = evaluation.get("teacherResponseChinese") or "这张卡完成得不错，可以结束本轮学习。"
    return {"evaluation": evaluation}


def save_answer(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    evaluation = state.get("evaluation", {})
    previous_attempts = cur.execute(
        "SELECT COUNT(*) AS count FROM answers WHERE session_id=? AND card_id=?",
        (state["session_id"], state["card_id"]),
    ).fetchone()["count"]
    attempt_number = int(state.get("attempt_number") or 0) or int(previous_attempts or 0) + 1
    cur.execute(
        "INSERT INTO answers (session_id,card_id,attempt_number,user_answer,score,evaluation_json,created_at) VALUES (?,?,?,?,?,?,?)",
        (
            state["session_id"],
            state["card_id"],
            attempt_number,
            state["user_answer"],
            evaluation.get("score", 0),
            json.dumps(evaluation, ensure_ascii=False),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {"attempt_number": attempt_number}


def load_round_data(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    session = cur.execute("SELECT * FROM sessions WHERE id=?", (state["session_id"],)).fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    card_rows = cur.execute("SELECT card_json FROM cards WHERE session_id=?", (state["session_id"],)).fetchall()
    answer_rows = cur.execute("SELECT card_id,attempt_number,user_answer,score,evaluation_json FROM answers WHERE session_id=?", (state["session_id"],)).fetchall()
    conn.close()

    cards = [json.loads(r["card_json"]) for r in card_rows]
    answers = []
    for r in answer_rows:
        evaluation = json.loads(r["evaluation_json"]) if r["evaluation_json"] else {}
        answers.append({
            "cardId": r["card_id"],
            "attemptNumber": r["attempt_number"],
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
    return {"round_data": round_data, "user_id": session["user_id"]}


def summarize_round(state, deps):
    prompt = build_round_summary_prompt(state["round_data"])
    summary = deps.ai_provider.summarize_round(prompt)
    return {"round_summary": summary.model_dump()}


def save_round_summary(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO round_summaries (session_id,summary_json,created_at) VALUES (?,?,?)",
        (state["session_id"], json.dumps(state["round_summary"], ensure_ascii=False), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return {}


def _dump_search_material(state: dict, search_results: list[dict]) -> Path:
    dump_dir = Path(__file__).resolve().parents[2] / "debug" / "search-material"
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_path = dump_dir / f"{state['session_id']}.json"
    payload = {
        "savedAt": datetime.utcnow().isoformat(),
        "sessionId": state.get("session_id"),
        "userId": state.get("user_id"),
        "topic": state.get("topic"),
        "level": state.get("level"),
        "searchQuery": state.get("search_query"),
        "searchResults": search_results,
    }
    dump_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return dump_path
