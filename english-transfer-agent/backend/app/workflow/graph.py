from __future__ import annotations

from dataclasses import dataclass

from langgraph.graph import START, END, StateGraph

from app.providers.ai import AiProvider
from app.providers.search import SearchProvider
from app.workflow.nodes import (
    build_search_query,
    check_novelty_against_memory,
    decide_memory_action,
    evaluate_answer,
    generate_learning_cards,
    load_memory,
    load_round_data,
    load_session_and_card,
    regenerate_cards_if_needed,
    save_answer,
    save_round_summary,
    save_session_and_cards,
    schedule_review,
    search_material_with_tavily,
    summarize_round,
    update_memory_from_evaluation,
    validate_cards,
)
from app.workflow.state import AgentState


@dataclass
class WorkflowDeps:
    ai_provider: AiProvider
    search_provider: SearchProvider


# State = shared workflow data carried across steps.
# Node = one concrete unit of work.
# Edge = ordered transition to next step.
# Graph = controlled learning workflow for each API phase.
def build_start_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("load_memory", lambda s: load_memory(s, deps))
    graph.add_node("build_search_query", lambda s: build_search_query(s, deps))
    graph.add_node("search_material_with_tavily", lambda s: search_material_with_tavily(s, deps))
    graph.add_node("generate_learning_cards", lambda s: generate_learning_cards(s, deps))
    graph.add_node("validate_cards", lambda s: validate_cards(s, deps))
    graph.add_node("check_novelty_against_memory", lambda s: check_novelty_against_memory(s, deps))
    graph.add_node("regenerate_cards_if_needed", lambda s: regenerate_cards_if_needed(s, deps))
    graph.add_node("save_session_and_cards", lambda s: save_session_and_cards(s, deps))

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "build_search_query")
    graph.add_edge("build_search_query", "search_material_with_tavily")
    graph.add_edge("search_material_with_tavily", "generate_learning_cards")
    graph.add_edge("generate_learning_cards", "validate_cards")
    graph.add_edge("validate_cards", "check_novelty_against_memory")
    graph.add_edge("check_novelty_against_memory", "regenerate_cards_if_needed")
    graph.add_edge("regenerate_cards_if_needed", "save_session_and_cards")
    graph.add_edge("save_session_and_cards", END)
    return graph.compile()


def build_answer_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("load_session_and_card", lambda s: load_session_and_card(s, deps))
    graph.add_node("evaluate_answer", lambda s: evaluate_answer(s, deps))
    graph.add_node("save_answer", lambda s: save_answer(s, deps))
    graph.add_node("decide_memory_action", lambda s: decide_memory_action(s, deps))
    graph.add_node("update_memory_from_evaluation", lambda s: update_memory_from_evaluation(s, deps))

    graph.add_edge(START, "load_session_and_card")
    graph.add_edge("load_session_and_card", "evaluate_answer")
    graph.add_edge("evaluate_answer", "save_answer")
    graph.add_edge("save_answer", "decide_memory_action")
    graph.add_edge("decide_memory_action", "update_memory_from_evaluation")
    graph.add_edge("update_memory_from_evaluation", END)
    return graph.compile()


def build_finish_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("load_round_data", lambda s: load_round_data(s, deps))
    graph.add_node("summarize_round", lambda s: summarize_round(s, deps))
    graph.add_node("save_round_summary", lambda s: save_round_summary(s, deps))
    graph.add_node("schedule_review", lambda s: schedule_review(s, deps))

    graph.add_edge(START, "load_round_data")
    graph.add_edge("load_round_data", "summarize_round")
    graph.add_edge("summarize_round", "save_round_summary")
    graph.add_edge("save_round_summary", "schedule_review")
    graph.add_edge("schedule_review", END)
    return graph.compile()
