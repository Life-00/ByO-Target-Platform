# 현재 진행된 agent 부분까지만 적용
# LangGraph 사용

from typing import TypedDict, Optional, Dict, List

from langgraph.graph import StateGraph, END

from app.schemas.fact import FactSet
from app.schemas.claim import ValidatedClaims
from app.agents.extractor.agent import ExtractorAgent
from app.agents.validator.agent import ValidatorAgent


# ======================================================
# Orchestrator State
# ======================================================
class OrchestratorState(TypedDict, total=False):
    # Input
    facts: FactSet

    # Output
    validated_claims: ValidatedClaims

    # Flow control
    need_more_retrieval: bool
    retrieval_hint: Optional[str]

    # For dialogue / summary
    validation_summary: Dict


# ======================================================
# Orchestrator Agent
# ======================================================
class OrchestratorAgent:
    """
    OrchestratorAgent
    -----------------
    - Agent execution order control
    - Validator input validation
    - Validation result interpretation
    - Decision for next step (proceed vs. re-retrieval)
    """

    def __init__(self):
        self.extractor = ExtractorAgent()
        self.validator = ValidatorAgent()
        self.graph = self._build_graph()

    # ==================================================
    # Graph construction
    # ==================================================
    def _build_graph(self) -> StateGraph:
        g = StateGraph(OrchestratorState)

        g.add_node("extract", self.node_extract)
        g.add_node("validate", self.node_validate)
        g.add_node("decide", self.node_decide)

        g.set_entry_point("extract")

        g.add_edge("extract", "validate")
        g.add_edge("validate", "decide")
        g.add_edge("decide", END)

        return g

    # ==================================================
    # Public entry point
    # ==================================================
    def run(self, facts: FactSet) -> OrchestratorState:
        initial_state: OrchestratorState = {
            "facts": facts,
            "need_more_retrieval": False,
        }
        return self.graph.invoke(initial_state)

    # ==================================================
    # Nodes
    # ==================================================
    def node_extract(self, state: OrchestratorState) -> OrchestratorState:
        """
        Extractor node
        - 현재는 facts가 이미 존재한다고 가정
        - 구조 유지 목적의 패스스루 노드
        """
        if "facts" not in state or state["facts"] is None:
            raise ValueError("Extractor reached without facts")
        return state

    def node_validate(self, state: OrchestratorState) -> OrchestratorState:
        """
        Validator 실행 전 입력 검증 + Validator 실행
        """
        facts = state.get("facts")

        # ---- Input validation (Orchestrator responsibility) ----
        if not facts or not facts.facts:
            state["validated_claims"] = ValidatedClaims(claims=[])
            return state

        for f in facts.facts:
            if not f.text:
                raise ValueError("Fact.text missing before validation")
            if not f.pmid:
                raise ValueError("Fact.pmid missing before validation")

        # ---- Validator execution ----
        validated = self.validator.run(facts)
        state["validated_claims"] = validated

        # ---- Summary for dialogue ----
        state["validation_summary"] = self._summarize_validation(validated)

        return state

    def node_decide(self, state: OrchestratorState) -> OrchestratorState:
        """
        Decide next action based on validation results
        """
        validated = state.get("validated_claims")

        need_more = False
        reasons: List[str] = []

        if validated:
            for claim in validated.claims:
                # Consistency-based decision
                if claim.consistency in {"conflicting", "insufficient"}:
                    need_more = True
                    reasons.append("conflicting_or_insufficient_evidence")

                # Risk-based decision (structure: Dict[str, List[str]])
                if "efficacy_failure" in claim.risk_signals:
                    need_more = True
                    reasons.append("efficacy_failure_signal")

        state["need_more_retrieval"] = need_more

        if need_more:
            state["retrieval_hint"] = (
                "Additional evidence required due to "
                + ", ".join(sorted(set(reasons)))
            )

        return state

    # ==================================================
    # Helpers
    # ==================================================
    def _summarize_validation(self, validated: ValidatedClaims) -> Dict:
        """
        Lightweight summary for DialogueAgent
        """
        summary = {
            "n_claims": len(validated.claims),
            "n_consistent": 0,
            "n_conflicting": 0,
            "n_insufficient": 0,
            "risk_counts": {},
        }

        for c in validated.claims:
            if c.consistency == "consistent":
                summary["n_consistent"] += 1
            elif c.consistency == "conflicting":
                summary["n_conflicting"] += 1
            elif c.consistency == "insufficient":
                summary["n_insufficient"] += 1

            for risk_type, keywords in c.risk_signals.items():
                summary["risk_counts"].setdefault(risk_type, 0)
                summary["risk_counts"][risk_type] += len(keywords)

        return summary

