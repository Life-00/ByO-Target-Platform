# app/agents/orchestrator/agent.py
from __future__ import annotations

import uuid
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.schemas.user_query import UserQuery
from app.schemas.paper import PaperCorpus
from app.schemas.fact import FactSet
from app.schemas.claim import ValidatedClaims
from app.schemas.dossier import TargetDossier, DossierSection

from app.services.pubmed.service import search_pubmed  # service layer
from app.agents.extractor.agent import ExtractorAgent
from app.agents.validator.agent import ValidatorAgent


class OrchestratorState(TypedDict, total=False):
    user_query: UserQuery
    corpus: PaperCorpus
    facts: FactSet
    validated_claims: ValidatedClaims
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


def node_validate(state: OrchestratorState) -> OrchestratorState:
    validator = ValidatorAgent()
    validated = validator.run(state["facts"])
    state["validated_claims"] = validated
    return state


def node_synthesize(state: OrchestratorState) -> OrchestratorState:
    """
    MVP synthesizer: FactSet을 그대로 '근거 요약(아주 단순)' 형태로 넣는다.
    (실제 SynthesizerAgent로 교체 예정)
    """
    uq = state["user_query"]
    validated = state.get("validated_claims")
    
    if not validated or not validated.claims:
        text_lines = ["- 검증된 주장이 없습니다."]
        citations = []
    else:
        # ValidatedClaim 기반으로 섹션 구성
        text_lines = []
        citations = []
        for vc in validated.claims:
            # Evidence summary
            ev_str = ", ".join([f"{k}:{v}" for k, v in vc.evidence_summary.items() if v > 0])
            line = f"### {vc.normalized_claim}\n- Consistency: {vc.consistency}\n- Evidence: {ev_str}"
            
            # Risk Signals
            if vc.risk_signals:
                risks = [f"{r.type} (severity: Medium)" for r in vc.risk_signals]
                line += f"\n- ⚠️ Risks: {', '.join(risks)}"
            
            text_lines.append(line)
            citations.extend([ev.pmid for ev in vc.evidence])

    citations = list(set(citations))

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
    g.add_node("validate", node_validate)
    g.add_node("synthesize", node_synthesize)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "extract")
    g.add_edge("extract", "validate")
    g.add_edge("validate", "synthesize")
    g.add_edge("synthesize", END)

    return g.compile()


class OrchestratorAgent:
    def __init__(self):
        self.graph = build_orchestrator_graph()

    def run(self, user_query: UserQuery) -> TargetDossier:
        final_state = self.graph.invoke({"user_query": user_query})
        return final_state["dossier"]
