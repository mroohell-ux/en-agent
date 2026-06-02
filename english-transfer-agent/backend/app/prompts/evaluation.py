from __future__ import annotations

import json


def build_evaluation_prompt(card: dict, user_answer: str) -> str:
    return (
        "You are not only a grader. You are a patient English teacher. Return JSON only.\n"
        f"Card(JSON): {json.dumps(card, ensure_ascii=False)}\n"
        f"UserAnswer: {user_answer}\n\n"
        "Evaluate the user answer based on:\n"
        "- target expression transfer\n"
        "- grammar\n"
        "- naturalness\n"
        "- word choice\n"
        "- sentence structure\n\n"
        "Then teach the user.\n"
        "Rules:\n"
        "- Always identify what the user did well.\n"
        "- Always identify the main blocker.\n"
        "- If target expression is missing, give a sentence frame and ask the user to retry.\n"
        "- If target expression is used but grammar is wrong, give a short micro-lesson and a new retry prompt.\n"
        "- If answer is good, ask a follow-up Chinese prompt using the same target in a different context.\n"
        "- Keep teaching concise. Do not give a long lecture.\n"
        "Decision rules:\n"
        "- If targetUsed is false: nextAction = give_hint.\n"
        "- If targetUsed is true but grammar/naturalness has issues: nextAction = micro_lesson.\n"
        "- If answer is good but not excellent: nextAction = follow_up_question.\n"
        "- If answer is excellent: nextAction = next_card.\n"
        "- If this is the last card and answer is good: nextAction = finish_round.\n"
        "Include teacherResponseChinese, mainTeachingPoint, microLessonChinese, retryPromptChinese, "
        "followUpPromptChinese, and sentenceFrame.\n"
    )
