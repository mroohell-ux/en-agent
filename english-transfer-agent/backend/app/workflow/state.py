from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    mode: str
    user_id: str
    session_id: str
    topic: str
    level: str

    card_id: str
    user_answer: str
    attempt_number: int

    search_query: str
    search_results: list[dict]

    cards: list[dict]
    filtered_cards: list[dict]
    current_card: dict
    is_last_card: bool

    evaluation: dict
    round_data: dict
    round_summary: dict

    error: str
