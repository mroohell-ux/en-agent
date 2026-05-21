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

    memory: dict
    search_query: str
    search_results: list[dict]

    cards: list[dict]
    filtered_cards: list[dict]
    current_card: dict

    evaluation: dict
    memory_action: str
    round_data: dict
    round_summary: dict

    novelty_score: int
    retry_count: int
    error: str
