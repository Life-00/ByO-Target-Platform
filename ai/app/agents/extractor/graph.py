# app/agents/extractor/graph.py
from __future__ import annotations

from langgraph.graph import StateGraph, END
from app.agents.extractor.state import ExtractorState
from app.agents.extractor.nodes import (
    iterate_sentences,
    extract_entities,
    extract_experiment,
    extract_relation,
    assemble_fact,
)


def build_extractor_graph():
    g = StateGraph(ExtractorState)

    g.add_node("iterate", iterate_sentences)
    g.add_node("entities", extract_entities)
    g.add_node("experiment", extract_experiment)
    g.add_node("relation", extract_relation)
    g.add_node("assemble", assemble_fact)

    g.set_entry_point("iterate")

    # 반복 루프: iterate -> (if current None => END) else continue
    def _has_sentence(state: ExtractorState) -> str:
        return "end" if state.get("current") is None else "go"

    g.add_conditional_edges(
        "iterate",
        _has_sentence,
        {"end": END, "go": "entities"},
    )

    g.add_edge("entities", "experiment")
    g.add_edge("experiment", "relation")
    g.add_edge("relation", "assemble")
    g.add_edge("assemble", "iterate")

    return g.compile()