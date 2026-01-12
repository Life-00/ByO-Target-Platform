# app/agents/extractor/agent.py
from __future__ import annotations

from app.schemas.paper import PaperCorpus
from app.schemas.fact import FactSet
from app.agents.extractor.graph import build_extractor_graph


class ExtractorAgent:
    def __init__(self):
        self.graph = build_extractor_graph()

    def run(self, corpus: PaperCorpus) -> FactSet:
        init_state = {
            "papers": corpus.papers,
            "extracted_facts": [],
        }
        final_state = self.graph.invoke(init_state)
        return FactSet(facts=final_state["extracted_facts"])