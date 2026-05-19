from __future__ import annotations

import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.db.memory_store import get_conn, get_memory, init_db, save_known, save_review
from app.prompts.evaluation import EVALUATION_PROMPT
from app.prompts.round_summary import ROUND_SUMMARY_PROMPT
from app.providers.ai import build_ai_provider
from app.providers.search import build_search_provider
from app.schemas import AnswerRequest, FinishRequest, StartRequest, StartResponse

load_dotenv()
app = FastAPI(title="english-transfer-agent")

search_provider = build_search_provider(os.getenv("SEARCH_PROVIDER", "mock"))
ai_provider = build_ai_provider(os.getenv("AI_PROVIDER", "mock"))


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/agent/start", response_model=StartResponse)
def start_agent(req: StartRequest) -> StartResponse:
    session_id = str(uuid.uuid4())
    query = f"well-written B2-C1 English short article {req.topic} not political"
    _ = search_provider.search(query, max_results=4)
    cards = ai_provider.generate_cards(query).cards

    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (req.userId,))
    cur.execute("INSERT INTO sessions (id,user_id,created_at) VALUES (?,?,?)", (session_id, req.userId, datetime.utcnow().isoformat()))
    for c in cards:
        cur.execute("INSERT INTO cards (id,session_id,target,type,topic) VALUES (?,?,?,?,?)", (c.id, session_id, c.target, c.type, req.topic))
    conn.commit(); conn.close()
    return StartResponse(sessionId=session_id, cards=cards)


@app.post("/agent/answer")
def answer_agent(req: AnswerRequest):
    conn = get_conn(); cur = conn.cursor()
    card = cur.execute("SELECT target FROM cards WHERE id=? AND session_id=?", (req.cardId, req.sessionId)).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    prompt = f"{EVALUATION_PROMPT}\nTarget:{card['target']}\nAnswer:{req.userAnswer}"
    evaluation = ai_provider.evaluate_answer(prompt)
    cur.execute("INSERT INTO answers (session_id,card_id,user_answer,score,created_at) VALUES (?,?,?,?,?)", (req.sessionId, req.cardId, req.userAnswer, evaluation.score, datetime.utcnow().isoformat()))

    session = cur.execute("SELECT user_id FROM sessions WHERE id=?", (req.sessionId,)).fetchone()
    if session and evaluation.memoryDecision.action == "mark_known":
        save_known(session["user_id"], "PATTERN", card["target"], req.cardId)
    elif session and evaluation.memoryDecision.action in {"save_for_review", "save_as_weak"}:
        save_review(session["user_id"], "PATTERN", card["target"], f"Practice: {card['target']}")

    conn.commit(); conn.close()
    return evaluation


@app.post("/agent/finish")
def finish_agent(req: FinishRequest):
    conn = get_conn(); cur = conn.cursor()
    session = cur.execute("SELECT user_id FROM sessions WHERE id=?", (req.sessionId,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    summary = ai_provider.summarize_round(ROUND_SUMMARY_PROMPT)
    cur.execute("INSERT INTO round_summaries (session_id,summary_json,created_at) VALUES (?,?,?)", (req.sessionId, summary.model_dump_json(), datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return summary


@app.post("/cards/{card_id}/mark-known")
def mark_known(card_id: str):
    conn = get_conn(); cur = conn.cursor()
    row = cur.execute("SELECT c.target,c.id,s.user_id FROM cards c JOIN sessions s ON c.session_id=s.id WHERE c.id=?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")
    save_known(row["user_id"], "PATTERN", row["target"], row["id"])
    return {"ok": True}


@app.get("/memory")
def read_memory(userId: str = "default-user"):
    return get_memory(userId)
