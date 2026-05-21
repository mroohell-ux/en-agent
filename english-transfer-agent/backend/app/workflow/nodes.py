from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException

from app.db.memory_store import get_conn, get_memory, save_known, save_review, save_weak_item
from app.prompts.card_generation import build_card_generation_prompt
from app.prompts.evaluation import build_evaluation_prompt
from app.prompts.round_summary import build_round_summary_prompt

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


def load_memory(state, deps):
    return {"memory": get_memory(state["user_id"])}


def build_search_query(state, deps):
    memory = state.get("memory", {})
    avoid = ", ".join(memory.get("knownTopics", [])[:3] + memory.get("knownPatterns", [])[:3] + memory.get("knownChunks", [])[:3])
    prefer = ", ".join(memory.get("weakGrammarPoints", [])[:3] + memory.get("weakPatterns", [])[:3])
    query = (
        f"well-written English article for {state['level']}, topic {state['topic']}, short to medium, "
        f"avoid political and too technical content, avoid known items: {avoid or 'none'}, "
        f"prefer naturally containing weak grammar/patterns: {prefer or 'none'}"
    )
    return {"search_query": query}


def search_material_with_tavily(state, deps):
    results = deps.search_provider.search(state["search_query"], max_results=5)
    return {"search_results": [r.model_dump() for r in results]}


def generate_learning_cards(state, deps):
    prompt = build_card_generation_prompt(
        topic=state["topic"],
        level=state["level"],
        search_results=state.get("search_results", []),
        memory=state.get("memory", {}),
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


def check_novelty_against_memory(state, deps):
    memory = state.get("memory", {})
    known = {x.lower().strip() for x in (memory.get("knownPatterns", []) + memory.get("knownChunks", []))}
    cards = state.get("filtered_cards", [])
    if not cards:
        return {"novelty_score": 0}

    repeated = 0
    total_checks = 0
    for card in cards:
        for field in ("target", "mustContain", "extractedFromOriginal"):
            total_checks += 1
            value = str(card.get(field, "")).lower().strip()
            if value and value in known:
                repeated += 1

    novelty_score = max(0, min(100, int(100 - (repeated / max(1, total_checks)) * 100)))
    return {"novelty_score": novelty_score}


def regenerate_cards_if_needed(state, deps):
    retry_count = state.get("retry_count", 0)
    novelty_score = state.get("novelty_score", 100)
    if novelty_score >= 70 or retry_count >= 1:
        return {}

    stronger_memory = dict(state.get("memory", {}))
    stronger_memory["knownPatterns"] = stronger_memory.get("knownPatterns", []) + ["STRICTLY_AVOID_KNOWN_ITEMS"]
    prompt = build_card_generation_prompt(
        topic=state["topic"],
        level=state["level"],
        search_results=state.get("search_results", []),
        memory=stronger_memory,
    ) + "\nExtra rule: Strictly avoid repeating any known targets or chunks."

    card_set = deps.ai_provider.generate_cards(prompt)
    valid_cards = []
    for card in [c.model_dump() for c in card_set.cards]:
        if len(valid_cards) >= 10:
            break
        if REQUIRED_CARD_FIELDS.issubset(card.keys()) and str(card.get("target", "")).strip() and str(card.get("chinesePrompt", "")).strip():
            valid_cards.append(card)
    if not valid_cards:
        return {"retry_count": retry_count + 1}
    return {"filtered_cards": valid_cards, "cards": valid_cards, "retry_count": retry_count + 1}


def save_session_and_cards(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (state["user_id"],))
    cur.execute(
        "INSERT INTO sessions (id,user_id,topic,created_at) VALUES (?,?,?,?)",
        (state["session_id"], state["user_id"], state["topic"], datetime.utcnow().isoformat()),
    )
    for card in state.get("filtered_cards", []):
        cur.execute(
            "INSERT INTO cards (id,session_id,target,type,topic,card_json,created_at) VALUES (?,?,?,?,?,?,?)",
            (
                card["id"],
                state["session_id"],
                card["target"],
                card["type"],
                state["topic"],
                json.dumps(card, ensure_ascii=False),
                datetime.utcnow().isoformat(),
            ),
        )
    conn.commit()
    conn.close()
    return {"cards": state.get("filtered_cards", [])}


def load_session_and_card(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    session = cur.execute("SELECT * FROM sessions WHERE id=?", (state["session_id"],)).fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    card_row = cur.execute("SELECT * FROM cards WHERE id=? AND session_id=?", (state["card_id"], state["session_id"])).fetchone()
    conn.close()
    if not card_row:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"current_card": json.loads(card_row["card_json"]), "user_id": session["user_id"]}


def evaluate_answer(state, deps):
    prompt = build_evaluation_prompt(state["current_card"], state["user_answer"])
    evaluation = deps.ai_provider.evaluate_answer(prompt)
    return {"evaluation": evaluation.model_dump()}


def save_answer(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    evaluation = state.get("evaluation", {})
    cur.execute(
        "INSERT INTO answers (session_id,card_id,user_answer,score,evaluation_json,created_at) VALUES (?,?,?,?,?,?)",
        (
            state["session_id"],
            state["card_id"],
            state["user_answer"],
            evaluation.get("score", 0),
            json.dumps(evaluation, ensure_ascii=False),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {}


def decide_memory_action(state, deps):
    action = state.get("evaluation", {}).get("memoryDecision", {}).get("action", "none")
    return {"memory_action": action}


def update_memory_from_evaluation(state, deps):
    action = state.get("memory_action", "none")
    eval_data = state.get("evaluation", {})
    card = state.get("current_card", {})
    target = card.get("target", "")
    user_id = state["user_id"]

    if action == "mark_known":
        save_known(user_id, "PATTERN", target, state["card_id"])
    elif action == "save_for_review":
        save_review(user_id, "PATTERN", target, f"Practice: {target}")
        for m in eval_data.get("mistakes", []):
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
    return {}


def load_round_data(state, deps):
    conn = get_conn()
    cur = conn.cursor()
    session = cur.execute("SELECT * FROM sessions WHERE id=?", (state["session_id"],)).fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    card_rows = cur.execute("SELECT card_json FROM cards WHERE session_id=?", (state["session_id"],)).fetchall()
    answer_rows = cur.execute("SELECT card_id,user_answer,score,evaluation_json FROM answers WHERE session_id=?", (state["session_id"],)).fetchall()
    conn.close()

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


def schedule_review(state, deps):
    for item in state.get("round_summary", {}).get("reviewPlan", []):
        save_review(
            state["user_id"],
            str(item.get("type", "Pattern")).upper(),
            item.get("item", ""),
            f"Review: {item.get('item', '')}",
            days=int(item.get("reviewAfterDays", 1)),
        )
    return {}
