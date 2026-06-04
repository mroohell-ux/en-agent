from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import HTTPException

from app.db.store import get_conn
from app.schemas import ArticleLesson, LessonProgress


def ingest_article(state, deps):
    text = (state.get("article_text") or "").strip()
    url = (state.get("article_url") or "").strip()
    if not text and not url:
        raise HTTPException(status_code=400, detail="Provide either articleText or articleUrl")
    if not text:
        text = f"Article supplied by URL: {url}. The teacher will build a speaking-first lesson from this source."
    return {"article_text": text, "article_url": url}


def extract_article_structure(state, deps):
    # The provider returns a complete draft; later nodes keep graph steps explicit and testable.
    lesson = deps.ai_provider.generate_article_lesson(_lesson_prompt(state)).model_dump()
    lesson["id"] = state["lesson_id"]
    lesson["userId"] = state["user_id"]
    lesson["level"] = state["level"]
    return {"article_lesson": lesson}


def generate_retell_task(state, deps):
    lesson = dict(state["article_lesson"])
    retell = lesson.get("retellTask") or {}
    retell.setdefault("prompt", "What is the main idea of this article? Say it in your own words.")
    retell.setdefault("targetSpeakingSeconds", 50)
    retell.setdefault("hints", ["Start with the main idea, then add why it matters."])
    retell.setdefault("expectedContentPoints", lesson.get("keyPoints", [])[:3])
    lesson["retellTask"] = retell
    return {"article_lesson": lesson}


def generate_teacher_questions(state, deps):
    lesson = dict(state["article_lesson"])
    questions = lesson.get("questions") or []
    required = {"comprehension", "explanation", "opinion", "personal_connection", "advanced_discussion"}
    present = {q.get("type") for q in questions}
    missing = required - present
    for qtype in sorted(missing):
        questions.append({
            "id": f"q-{qtype}",
            "type": qtype,
            "question": "What can you say about this part of the article?",
            "expectedIdeas": ["Answer from the article", "Add one clear reason"],
            "usefulExpressionHint": None,
        })
    lesson["questions"] = questions
    return {"article_lesson": lesson}


def extract_useful_language(state, deps):
    lesson = dict(state["article_lesson"])
    lesson["usefulLanguage"] = (lesson.get("usefulLanguage") or [])[:10]
    if len(lesson["usefulLanguage"]) < 5:
        raise HTTPException(status_code=400, detail="At least five useful-language items are required")
    return {"article_lesson": lesson}


def generate_optional_ielts_tasks(state, deps):
    lesson = dict(state["article_lesson"])
    if not state.get("include_ielts"):
        lesson["ieltsTasks"] = None
    return {"article_lesson": lesson}


def validate_article_lesson(state, deps):
    lesson = ArticleLesson.model_validate(state["article_lesson"])
    if len(lesson.questions) < 5:
        raise HTTPException(status_code=400, detail="Article lesson needs at least five teacher questions")
    return {"article_lesson": lesson.model_dump()}


def save_article_lesson(state, deps):
    lesson = ArticleLesson.model_validate(state["article_lesson"])
    now = datetime.utcnow().isoformat()
    source_id = f"source-{lesson.id}"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (lesson.userId,))
    cur.execute(
        "INSERT OR REPLACE INTO article_sources (id,lesson_id,title,url,site,raw_text,published_at,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (source_id, lesson.id, lesson.source.title, lesson.source.url, lesson.source.site, lesson.source.rawText, lesson.source.publishedAt, now),
    )
    cur.execute(
        "INSERT OR REPLACE INTO article_lessons (id,user_id,level,source_id,main_idea,key_points_json,retell_task_json,ielts_tasks_json,progress_json,lesson_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (lesson.id, lesson.userId, lesson.level, source_id, lesson.mainIdea, json.dumps(lesson.keyPoints, ensure_ascii=False), lesson.retellTask.model_dump_json(), lesson.ieltsTasks.model_dump_json() if lesson.ieltsTasks else None, lesson.progress.model_dump_json(), lesson.model_dump_json(), now, now),
    )
    for question in lesson.questions:
        cur.execute(
            "INSERT OR REPLACE INTO teacher_questions (id,lesson_id,type,question,question_json,created_at) VALUES (?,?,?,?,?,?)",
            (question.id, lesson.id, question.type, question.question, question.model_dump_json(), now),
        )
    for item in lesson.usefulLanguage:
        cur.execute(
            "INSERT OR REPLACE INTO useful_language_items (id,lesson_id,category,text,item_json,created_at) VALUES (?,?,?,?,?,?)",
            (item.id, lesson.id, item.category, item.text, item.model_dump_json(), now),
        )
    conn.commit()
    conn.close()
    return {"article_lesson": lesson.model_dump()}


def load_lesson_task(state, deps):
    lesson = _load_lesson(state["lesson_id"])
    task_type = state["task_type"]
    task_id = state["task_id"]
    task = lesson.get("retellTask") if task_type == "retell" else None
    if task_type == "question":
        task = next((q for q in lesson.get("questions", []) if q.get("id") == task_id), None)
    if task_type == "useful_language":
        task = next((i for i in lesson.get("usefulLanguage", []) if i.get("id") == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Lesson task not found")
    return {"article_lesson": lesson, "lesson_task": task}


def evaluate_user_transcript(state, deps):
    prompt = _speaking_prompt(state)
    correction = deps.ai_provider.evaluate_speaking_answer(prompt).model_dump()
    return {"teacher_correction": correction}


def generate_corrections(state, deps):
    correction = dict(state["teacher_correction"])
    correction.setdefault("keyImprovements", [])
    correction.setdefault("mistakes", [])
    return {"teacher_correction": correction}


def generate_repeat_prompt(state, deps):
    correction = dict(state["teacher_correction"])
    if not correction.get("repeatPrompt"):
        correction["repeatPrompt"] = f"Now repeat this improved version aloud: {correction.get('naturalVersion', '')}"
    correction["nextAction"] = correction.get("nextAction") or "repeat_better_version"
    return {"teacher_correction": correction}


def save_answer_and_mistakes(state, deps):
    now = datetime.utcnow().isoformat()
    answer_id = str(uuid.uuid4())
    correction_id = str(uuid.uuid4())
    correction = state["teacher_correction"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO speaking_answers (id,lesson_id,task_type,task_id,attempt_number,transcript,created_at) VALUES (?,?,?,?,?,?,?)",
        (answer_id, state["lesson_id"], state["task_type"], state["task_id"], state.get("attempt_number") or 1, state["transcript"], now),
    )
    cur.execute(
        "INSERT INTO teacher_corrections (id,answer_id,lesson_id,task_type,task_id,score,correction_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (correction_id, answer_id, state["lesson_id"], state["task_type"], state["task_id"], correction.get("score", 0), json.dumps(correction, ensure_ascii=False), now),
    )
    for mistake in correction.get("mistakes", []):
        cur.execute(
            "INSERT INTO lesson_mistakes (id,lesson_id,answer_id,type,original,correction,mistake_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), state["lesson_id"], answer_id, mistake.get("type"), mistake.get("original"), mistake.get("correction"), json.dumps(mistake, ensure_ascii=False), now),
        )
    _update_progress(cur, state["lesson_id"], state["task_type"], state["task_id"], len(correction.get("mistakes", [])))
    conn.commit()
    conn.close()
    return {"answer_id": answer_id}


def load_lesson_history(state, deps):
    lesson = _load_lesson(state["lesson_id"])
    conn = get_conn()
    cur = conn.cursor()
    answer_rows = cur.execute("SELECT * FROM speaking_answers WHERE lesson_id=? ORDER BY created_at", (state["lesson_id"],)).fetchall()
    correction_rows = cur.execute("SELECT * FROM teacher_corrections WHERE lesson_id=? ORDER BY created_at", (state["lesson_id"],)).fetchall()
    mistake_rows = cur.execute("SELECT * FROM lesson_mistakes WHERE lesson_id=? ORDER BY created_at", (state["lesson_id"],)).fetchall()
    conn.close()
    return {
        "article_lesson": lesson,
        "lesson_history": {
            "answers": [dict(r) for r in answer_rows],
            "corrections": [json.loads(r["correction_json"]) for r in correction_rows],
            "mistakes": [json.loads(r["mistake_json"]) for r in mistake_rows],
        },
    }


def summarize_lesson(state, deps):
    summary = deps.ai_provider.summarize_article_lesson(_summary_prompt(state)).model_dump()
    summary["lessonId"] = state["lesson_id"]
    return {"lesson_summary": summary}


def save_lesson_summary(state, deps):
    now = datetime.utcnow().isoformat()
    summary = state["lesson_summary"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO lesson_summaries (id,lesson_id,summary_json,created_at) VALUES (?,?,?,?)", (str(uuid.uuid4()), state["lesson_id"], json.dumps(summary, ensure_ascii=False), now))
    row = cur.execute("SELECT progress_json FROM article_lessons WHERE id=?", (state["lesson_id"],)).fetchone()
    progress = LessonProgress.model_validate(json.loads(row["progress_json"]) if row and row["progress_json"] else {}).model_dump()
    progress["stage"] = "finished"
    cur.execute("UPDATE article_lessons SET progress_json=?, updated_at=? WHERE id=?", (json.dumps(progress, ensure_ascii=False), now, state["lesson_id"]))
    conn.commit()
    conn.close()
    return {}


def list_article_lessons(user_id: str = "default-user") -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT lesson_json, progress_json FROM article_lessons WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    lessons = []
    for row in rows:
        lesson = json.loads(row["lesson_json"])
        if row["progress_json"]:
            lesson["progress"] = json.loads(row["progress_json"])
        lessons.append(lesson)
    return lessons


def _load_lesson(lesson_id: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT lesson_json, progress_json FROM article_lessons WHERE id=?", (lesson_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Article lesson not found")
    lesson = json.loads(row["lesson_json"])
    if row["progress_json"]:
        lesson["progress"] = json.loads(row["progress_json"])
    return lesson


def _update_progress(cur, lesson_id: str, task_type: str, task_id: str, mistake_count: int) -> None:
    row = cur.execute("SELECT progress_json FROM article_lessons WHERE id=?", (lesson_id,)).fetchone()
    progress = LessonProgress.model_validate(json.loads(row["progress_json"]) if row and row["progress_json"] else {}).model_dump()
    progress["stage"] = "retell" if task_type == "retell" else "questions" if task_type == "question" else "useful_language"
    progress["answerCount"] = int(progress.get("answerCount") or 0) + 1
    progress["mistakeCount"] = int(progress.get("mistakeCount") or 0) + mistake_count
    completed = set(progress.get("completedTaskIds") or [])
    completed.add(task_id)
    progress["completedTaskIds"] = sorted(completed)
    if task_type == "useful_language":
        learned = set(progress.get("learnedUsefulLanguageIds") or [])
        learned.add(task_id)
        progress["learnedUsefulLanguageIds"] = sorted(learned)
    cur.execute("UPDATE article_lessons SET progress_json=?, updated_at=? WHERE id=?", (json.dumps(progress, ensure_ascii=False), datetime.utcnow().isoformat(), lesson_id))


def _lesson_prompt(state) -> str:
    return "\n".join([
        "Build an article-based English speaking lesson. The article is source material; user output is the center.",
        f"UserId: {state['user_id']}",
        f"Level: {state['level']}",
        f"ArticleUrl: {state.get('article_url') or ''}",
        f"IncludeIelts: {str(bool(state.get('include_ielts'))).lower()}",
        "ArticleText:",
        state.get("article_text") or "",
    ])


def _speaking_prompt(state) -> str:
    return "\n".join([
        "You are a strict but friendly English speaking coach. Prioritize naturalness and active speaking.",
        f"LessonId: {state['lesson_id']}",
        f"TaskType: {state['task_type']}",
        f"TaskId: {state['task_id']}",
        f"Task: {json.dumps(state.get('lesson_task', {}), ensure_ascii=False)}",
        "Evaluate whether the answer addresses the article, has clear logic, and sounds natural.",
        "Transcript:",
        state.get("transcript") or "",
    ])


def _summary_prompt(state) -> str:
    return "\n".join([
        "Summarize this article speaking lesson for review.",
        f"LessonId: {state['lesson_id']}",
        f"Lesson: {json.dumps(state.get('article_lesson', {}), ensure_ascii=False)}",
        f"History: {json.dumps(state.get('lesson_history', {}), ensure_ascii=False)}",
    ])
