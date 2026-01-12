# LangGraph 사용
from typing import TypedDict, Optional, Dict, List

from langgraph.graph import StateGraph, END

from app.schemas.fact import FactSet
from app.schemas.claim import ValidatedClaims
from app.schemas.paper import PaperCorpus
from app.schemas.user_query import UserQuery
from app.schemas.dossier import TargetDossier

from app.agents.retriever.agent import RetrieverAgent
from app.agents.extractor.agent import ExtractorAgent
from app.agents.validator.agent import ValidatorAgent
from app.agents.synthesizer.agent import SynthesizerAgent

# ======================================================
# Orchestrator State
# ======================================================
class OrchestratorState(TypedDict, total=False):
    # Input
    user_query: UserQuery
    facts: FactSet

    # Intermediate
    paper_corpus: PaperCorpus

    # Output
    validated_claims: ValidatedClaims

    # Flow control
    need_more_retrieval: bool
    retrieval_hint: Optional[str]

    # 재검색
    retrieval_round: int

    # For dialogue / summary
    validation_summary: Dict

    # target dossier
    target_dossier: Optional[TargetDossier]


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
        self.retriever = RetrieverAgent()
        self.extractor = ExtractorAgent()
        self.validator = ValidatorAgent()
        self.graph = self._build_graph()
        self.synthesizer = SynthesizerAgent()


    # ==================================================
    # Public entry point
    # ==================================================
    def run(self,
            facts: Optional[FactSet] = None,
            user_query: Optional[UserQuery] = None,) -> OrchestratorState:
        # user_query가 여러 step에서 중복 write 가능
        # -> Orchestrator에서 user_query는 READ ONLY (명시적 보호)
        if not facts and not user_query:
            raise ValueError("Either facts or user_query must be provided")

        initial_state: OrchestratorState = {
            "facts": facts,
            "user_query": user_query,
            "need_more_retrieval": False,
            "retrieval_round": 0,
        }
        return self.graph.invoke(initial_state)

    # ==================================================
    # Nodes
    # ==================================================
    def node_retrieve(self, state: OrchestratorState) -> OrchestratorState:
        if state.get("need_more_retrieval"):
            state["retrieval_round"] += 1

        user_query = state.get("user_query")
        if user_query is None:
            raise ValueError("Retriever reached without user_query")

        paper_corpus = self.retriever.run(user_query)
        state["paper_corpus"] = paper_corpus

        # 재검색 플래그 리셋
        state["need_more_retrieval"] = False
        state["retrieval_hint"] = None

        return state


    def node_extract(self, state: OrchestratorState) -> OrchestratorState:
        """
        Extractor node
        - 현재는 facts가 이미 존재한다고 가정
        - 구조 유지 목적의 패스스루 노드
        """
        paper_corpus = state.get("paper_corpus")
        if not paper_corpus:
            raise ValueError("Extractor reached without paper_corpus")

        facts = self.extractor.run(paper_corpus)
        state["facts"] = facts

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

                # Risk-based decision (List[RiskSignal])
                for risk in claim.risk_signals:
                    if risk.type == "efficacy_failure":
                        need_more = True
                        reasons.append("efficacy_failure_signal")

        state["need_more_retrieval"] = need_more

        HINT_MAP = {
            "conflicting_or_insufficient_evidence": "일부 주장이 서로 상충하거나 근거가 부족합니다",
            "efficacy_failure_signal": "일부 연구에서 효능 실패 신호가 보고되었습니다",
        }

        if need_more:
            human_reasons = [HINT_MAP[r] for r in set(reasons) if r in HINT_MAP]
            state["retrieval_hint"] = " / ".join(human_reasons)

        return state

    def node_synthesize(self, state: OrchestratorState) -> OrchestratorState:
        validated = state.get("validated_claims")
        uq = state.get("user_query")

        if not validated or not uq:
            return state

        dossier = self.synthesizer.run(
            validated,
            target=uq.target,
        )
        state["target_dossier"] = dossier
        return state

    # ==================================================
    # Graph construction
    # ==================================================
    def _build_graph(self) -> StateGraph:
        g = StateGraph(OrchestratorState)

        g.add_node("retrieve", self.node_retrieve)
        g.add_node("extract", self.node_extract)
        g.add_node("validate", self.node_validate)
        g.add_node("decide", self.node_decide)

        g.set_entry_point("retrieve")

        g.add_edge("retrieve", "extract")
        g.add_edge("extract", "validate")
        g.add_edge("validate", "decide")

        g.add_node("synthesize", self.node_synthesize)
        g.add_conditional_edges(
            "decide",
            self._route_after_decide,
            {
                "retrieve": "retrieve",
                "synthesize": "synthesize",
            }
        )
        g.add_edge("synthesize", END)

        return g.compile()

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

            for rs in c.risk_signals:
                summary["risk_counts"][rs.type] = (
                        summary["risk_counts"].get(rs.type, 0) + len(rs.keywords)
                )

        return summary

    # ==================================================
    # 재검색
    # ==================================================
    def _route_after_decide(self, state: OrchestratorState) -> str:
        """
        Decide next step after validation.
        """
        MAX_RETRIEVAL_ROUNDS = 3  # 안전장치

        if state.get("need_more_retrieval") and state.get("retrieval_round", 0) < MAX_RETRIEVAL_ROUNDS:
            return "retrieve"

        return "synthesize"
