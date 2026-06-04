from fastapi.testclient import TestClient

from app.db.store import init_db
from app.main import app
from app.providers.ai import MockAiProvider
from app.schemas import ArticleLesson, TeacherCorrection


ARTICLE = """JD Vance's old comment about childless cat ladies unleashed fury online.
Critics took issue with it because they saw it as sexist. The comment did not land well
and raised questions about who has a direct stake in society."""


def test_mock_provider_generates_article_lesson_questions_and_useful_language():
    lesson = MockAiProvider().generate_article_lesson(
        "UserId: default-user\nLevel: B2-C1\nArticleUrl: \nIncludeIelts: true\nArticleText:\n" + ARTICLE
    )

    assert isinstance(lesson, ArticleLesson)
    assert lesson.retellTask.prompt.startswith("What is the main idea")
    assert {question.type for question in lesson.questions} == {
        "comprehension",
        "explanation",
        "opinion",
        "personal_connection",
        "advanced_discussion",
    }
    useful_text = {item.text for item in lesson.usefulLanguage}
    assert {"unleash fury", "did not land well", "take issue with", "have a direct stake in"}.issubset(useful_text)
    assert lesson.ieltsTasks is not None


def test_mock_provider_evaluates_speaking_answer_with_reviewable_mistakes():
    correction = MockAiProvider().evaluate_speaking_answer(
        "TaskType: retell\nTaskId: retell-main-idea\nTranscript:\nPeople angry about the bad history and it is sexist."
    )

    assert isinstance(correction, TeacherCorrection)
    assert correction.score < 90
    assert correction.nextAction == "repeat_better_version"
    assert any(mistake.reviewItem == "people angry about → backlash against" for mistake in correction.mistakes)


def test_article_lesson_api_flow():
    init_db()
    client = TestClient(app)

    lesson_res = client.post(
        "/lessons/from-article",
        json={"userId": "test-user", "level": "B2-C1", "articleText": ARTICLE, "includeIelts": True},
    )
    assert lesson_res.status_code == 200
    lesson = lesson_res.json()
    assert lesson["questions"]
    assert lesson["usefulLanguage"]

    retell_res = client.post(
        f"/lessons/{lesson['id']}/retell",
        json={"transcript": "People angry about the comment because it is sexist.", "attemptNumber": 1},
    )
    assert retell_res.status_code == 200
    correction = retell_res.json()
    assert correction["repeatPrompt"].startswith("Now repeat")
    assert correction["mistakes"]

    summary_res = client.post(f"/lessons/{lesson['id']}/finish")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["whatUserDidWell"]
    assert summary["suggestedNextPractice"]
