# app/agents/orchestrator/agent.py
from __future__ import annotations

import uuid
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.schemas.user_query import UserQuery
from app.schemas.paper import PaperCorpus
from app.schemas.fact import FactSet
from app.schemas.dossier import TargetDossier, DossierSection

from app.services.pubmed.service import search_pubmed  # service layer
from app.agents.extractor.agent import ExtractorAgent


class OrchestratorState(TypedDict, total=False):
    user_query: UserQuery
    corpus: PaperCorpus
    facts: FactSet
    dossier: TargetDossier


def node_retrieve(state: OrchestratorState) -> OrchestratorState:
    uq = state["user_query"]
    corpus = search_pubmed(uq)  # PaperCorpus 반환하도록 service를 맞추는 것을 권장
    state["corpus"] = corpus
    return state


def node_extract(state: OrchestratorState) -> OrchestratorState:
    extractor = ExtractorAgent()
    facts = extractor.run(state["corpus"])
    state["facts"] = facts
    return state


def node_synthesize(state: OrchestratorState) -> OrchestratorState:
    """
    MVP synthesizer: FactSet을 그대로 '근거 요약(아주 단순)' 형태로 넣는다.
    (실제 SynthesizerAgent로 교체 예정)
    """
    uq = state["user_query"]
    facts = state["facts"]

    # 아주 단순한 섹션 구성 (citation은 PMID 기반)
    pmids = list({f.pmid for f in facts.facts})
    text_lines = [
        f"- PMID {f.pmid} / sent {f.sentence_id}: {f.text}"
        for f in facts.facts[:20]
    ] or ["- 추출된 fact가 없습니다. 검색 범위를 조정해 보세요."]

    dossier = TargetDossier(
        dossier_id=str(uuid.uuid4()),
        target=uq.target,
        sections={
            "KeyFacts": [DossierSection(text="\n".join(text_lines), citations=pmids)]
        },
        format="markdown",
    )
    state["dossier"] = dossier
    return state


def build_orchestrator_graph():
    g = StateGraph(OrchestratorState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("extract", node_extract)
    g.add_node("synthesize", node_synthesize)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "extract")
    g.add_edge("extract", "synthesize")
    g.add_edge("synthesize", END)

    return g.compile()


class OrchestratorAgent:
    def __init__(self):
        self.graph = build_orchestrator_graph()

    def run(self, user_query: UserQuery) -> TargetDossier:
        final_state = self.graph.invoke({"user_query": user_query})
        return final_state["dossier"]
