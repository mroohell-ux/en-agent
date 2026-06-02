from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from langgraph.graph import START, END, StateGraph

from app.providers.ai import AiProvider
from app.providers.search import SearchProvider
from app.workflow.nodes import (
    build_search_query,
    evaluate_answer,
    generate_learning_cards,
    load_round_data,
    load_session_and_card,
    save_answer,
    save_round_summary,
    save_session_and_cards,
    search_material_with_tavily,
    summarize_round,
    validate_cards,
)
from app.workflow.state import AgentState


@dataclass
class WorkflowDeps:
    ai_provider: AiProvider
    search_provider: SearchProvider


def step_node(step_label: str, func):
    def run(state):
        try:
            return func(state)
        except HTTPException as exc:
            if isinstance(exc.detail, dict) and exc.detail.get("step"):
                raise
            raise HTTPException(
                status_code=exc.status_code,
                detail={"step": step_label, "rootCause": str(exc.detail)},
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={"step": step_label, "rootCause": str(exc)},
            ) from exc

    return run


# State = shared workflow data carried across steps.
# Node = one concrete unit of work.
# Edge = ordered transition to next step.
# Graph = controlled learning workflow for each API phase.
def build_start_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("build_search_query", step_node("Build search query", lambda s: build_search_query(s, deps)))
    graph.add_node("search_material_with_tavily", step_node("Find English source material", lambda s: search_material_with_tavily(s, deps)))
    graph.add_node("generate_learning_cards", step_node("Generate practice cards", lambda s: generate_learning_cards(s, deps)))
    graph.add_node("validate_cards", step_node("Validate generated cards", lambda s: validate_cards(s, deps)))
    graph.add_node("save_session_and_cards", step_node("Save practice round", lambda s: save_session_and_cards(s, deps)))

    graph.add_edge(START, "build_search_query")
    graph.add_edge("build_search_query", "search_material_with_tavily")
    graph.add_edge("search_material_with_tavily", "generate_learning_cards")
    graph.add_edge("generate_learning_cards", "validate_cards")
    graph.add_edge("validate_cards", "save_session_and_cards")
    graph.add_edge("save_session_and_cards", END)
    return graph.compile()


def build_answer_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("load_session_and_card", step_node("Load your practice card", lambda s: load_session_and_card(s, deps)))
    graph.add_node("evaluate_answer", step_node("Evaluate your answer", lambda s: evaluate_answer(s, deps)))
    graph.add_node("save_answer", step_node("Save your answer", lambda s: save_answer(s, deps)))

    graph.add_edge(START, "load_session_and_card")
    graph.add_edge("load_session_and_card", "evaluate_answer")
    graph.add_edge("evaluate_answer", "save_answer")
    graph.add_edge("save_answer", END)
    return graph.compile()


def build_finish_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("load_round_data", step_node("Load round history", lambda s: load_round_data(s, deps)))
    graph.add_node("summarize_round", step_node("Summarize your round", lambda s: summarize_round(s, deps)))
    graph.add_node("save_round_summary", step_node("Save round summary", lambda s: save_round_summary(s, deps)))

    graph.add_edge(START, "load_round_data")
    graph.add_edge("load_round_data", "summarize_round")
    graph.add_edge("summarize_round", "save_round_summary")
    graph.add_edge("save_round_summary", END)
    return graph.compile()
