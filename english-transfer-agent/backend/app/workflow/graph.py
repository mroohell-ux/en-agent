from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from langgraph.graph import START, END, StateGraph

from app.providers.ai import AiProvider
from app.providers.search import SearchProvider
from app.workflow.article_nodes import (
    evaluate_user_transcript,
    extract_article_structure,
    extract_useful_language,
    generate_corrections,
    generate_optional_ielts_tasks,
    generate_repeat_prompt,
    generate_retell_task,
    generate_teacher_questions,
    ingest_article,
    load_lesson_history,
    load_lesson_task,
    save_answer_and_mistakes,
    save_article_lesson,
    save_lesson_summary,
    summarize_lesson,
    validate_article_lesson,
)
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



def build_article_lesson_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("ingest_article", step_node("Ingest article", lambda s: ingest_article(s, deps)))
    graph.add_node("extract_article_structure", step_node("Extract article structure", lambda s: extract_article_structure(s, deps)))
    graph.add_node("generate_retell_task", step_node("Generate retell task", lambda s: generate_retell_task(s, deps)))
    graph.add_node("generate_teacher_questions", step_node("Generate teacher questions", lambda s: generate_teacher_questions(s, deps)))
    graph.add_node("extract_useful_language", step_node("Extract useful language", lambda s: extract_useful_language(s, deps)))
    graph.add_node("generate_optional_ielts_tasks", step_node("Generate optional IELTS tasks", lambda s: generate_optional_ielts_tasks(s, deps)))
    graph.add_node("validate_article_lesson", step_node("Validate article lesson", lambda s: validate_article_lesson(s, deps)))
    graph.add_node("save_article_lesson", step_node("Save article lesson", lambda s: save_article_lesson(s, deps)))

    graph.add_edge(START, "ingest_article")
    graph.add_edge("ingest_article", "extract_article_structure")
    graph.add_edge("extract_article_structure", "generate_retell_task")
    graph.add_edge("generate_retell_task", "generate_teacher_questions")
    graph.add_edge("generate_teacher_questions", "extract_useful_language")
    graph.add_edge("extract_useful_language", "generate_optional_ielts_tasks")
    graph.add_edge("generate_optional_ielts_tasks", "validate_article_lesson")
    graph.add_edge("validate_article_lesson", "save_article_lesson")
    graph.add_edge("save_article_lesson", END)
    return graph.compile()


def build_speaking_evaluation_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("load_lesson_task", step_node("Load lesson task", lambda s: load_lesson_task(s, deps)))
    graph.add_node("evaluate_user_transcript", step_node("Evaluate user transcript", lambda s: evaluate_user_transcript(s, deps)))
    graph.add_node("generate_corrections", step_node("Generate corrections", lambda s: generate_corrections(s, deps)))
    graph.add_node("generate_repeat_prompt", step_node("Generate repeat prompt", lambda s: generate_repeat_prompt(s, deps)))
    graph.add_node("save_answer_and_mistakes", step_node("Save answer and mistakes", lambda s: save_answer_and_mistakes(s, deps)))

    graph.add_edge(START, "load_lesson_task")
    graph.add_edge("load_lesson_task", "evaluate_user_transcript")
    graph.add_edge("evaluate_user_transcript", "generate_corrections")
    graph.add_edge("generate_corrections", "generate_repeat_prompt")
    graph.add_edge("generate_repeat_prompt", "save_answer_and_mistakes")
    graph.add_edge("save_answer_and_mistakes", END)
    return graph.compile()


def build_lesson_finish_graph(deps: WorkflowDeps):
    graph = StateGraph(AgentState)
    graph.add_node("load_lesson_history", step_node("Load lesson history", lambda s: load_lesson_history(s, deps)))
    graph.add_node("summarize_lesson", step_node("Summarize lesson", lambda s: summarize_lesson(s, deps)))
    graph.add_node("save_lesson_summary", step_node("Save lesson summary", lambda s: save_lesson_summary(s, deps)))

    graph.add_edge(START, "load_lesson_history")
    graph.add_edge("load_lesson_history", "summarize_lesson")
    graph.add_edge("summarize_lesson", "save_lesson_summary")
    graph.add_edge("save_lesson_summary", END)
    return graph.compile()
