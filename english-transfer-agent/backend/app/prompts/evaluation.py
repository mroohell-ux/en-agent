from __future__ import annotations

import json


def build_evaluation_prompt(card: dict, user_answer: str) -> str:
    return (
        "Evaluate the user's English answer. Return JSON only.\n"
        f"Card(JSON): {json.dumps(card, ensure_ascii=False)}\n"
        f"UserAnswer: {user_answer}\n\n"
        "Check:\n"
        "- target pattern/chunk/grammar usage\n"
        "- grammar errors\n"
        "- unnatural expression\n"
        "- word choice\n"
        "- sentence structure\n"
        "- corrected answer\n"
        "- natural version\n"
        "- advanced version\n"
        "- memoryDecision (mark_known | save_for_review | save_as_weak | none)\n"
    )
