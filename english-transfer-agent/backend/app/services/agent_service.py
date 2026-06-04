from __future__ import annotations

import uuid

from fastapi import HTTPException

from app.schemas import (
    AnswerEvaluation,
    AnswerRequest,
    ArticleLesson,
    ArticleLessonRequest,
    FinishRequest,
    LearningCard,
    LessonSummary,
    RoundSummary,
    SpeakingAnswerRequest,
    StartRequest,
    StartResponse,
    TeacherCorrection,
)
from app.workflow.article_nodes import list_article_lessons
from app.workflow.graph import (
    WorkflowDeps,
    build_answer_graph,
    build_article_lesson_graph,
    build_finish_graph,
    build_lesson_finish_graph,
    build_speaking_evaluation_graph,
    build_start_graph,
)


class AgentService:
    def __init__(self, ai_provider, search_provider) -> None:
        deps = WorkflowDeps(ai_provider=ai_provider, search_provider=search_provider)
        self.start_graph = build_start_graph(deps)
        self.answer_graph = build_answer_graph(deps)
        self.finish_graph = build_finish_graph(deps)
        self.article_lesson_graph = build_article_lesson_graph(deps)
        self.speaking_evaluation_graph = build_speaking_evaluation_graph(deps)
        self.lesson_finish_graph = build_lesson_finish_graph(deps)

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


    def create_article_lesson(self, req: ArticleLessonRequest) -> ArticleLesson:
        lesson_id = str(uuid.uuid4())
        state = self.article_lesson_graph.invoke(
            {
                "mode": "article_lesson",
                "lesson_id": lesson_id,
                "user_id": req.userId,
                "level": req.level,
                "article_url": req.articleUrl,
                "article_text": req.articleText,
                "include_ielts": req.includeIelts,
            }
        )
        return ArticleLesson(**state["article_lesson"])

    def list_article_lessons(self, user_id: str = "default-user") -> list[ArticleLesson]:
        return [ArticleLesson(**lesson) for lesson in list_article_lessons(user_id)]

    def evaluate_speaking(self, req: SpeakingAnswerRequest) -> TeacherCorrection:
        state = self.speaking_evaluation_graph.invoke(
            {
                "mode": "speaking_answer",
                "lesson_id": req.lessonId,
                "task_type": req.taskType,
                "task_id": req.taskId,
                "transcript": req.transcript,
                "attempt_number": req.attemptNumber,
            }
        )
        return TeacherCorrection(**state["teacher_correction"])

    def finish_lesson(self, lesson_id: str) -> LessonSummary:
        state = self.lesson_finish_graph.invoke({"mode": "lesson_finish", "lesson_id": lesson_id})
        return LessonSummary(**state["lesson_summary"])
