from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, END


class AgentState(TypedDict, total=False):
    memory: dict
    search_results: list
    references: list
    cards: list
    novelty_score: int


def build_learning_graph():
    g = StateGraph(AgentState)

    nodes = [
        "load_memory",
        "search_material_with_tavily",
        "select_references",
        "generate_learning_cards",
        "validate_cards",
        "check_novelty_against_memory",
        "return_cards",
        "wait_for_user_answer",
        "evaluate_answer",
        "decide_memory_action",
        "update_card_result",
        "finish_round",
        "update_memory",
        "schedule_review",
    ]

    for n in nodes:
        g.add_node(n, lambda s, _n=n: s)

    g.set_entry_point("load_memory")
    for a, b in zip(nodes, nodes[1:]):
        g.add_edge(a, b)
    g.add_edge("schedule_review", END)

    return g.compile()
