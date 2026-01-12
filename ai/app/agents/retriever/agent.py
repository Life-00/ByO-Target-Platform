from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.agents.retriever.state import RetrieverState
from app.schemas.user_query import UserQuery
from app.schemas.paper import PaperCorpus
from app.services.pubmed.service import search_pubmed


class RetrieverAgent:
    """
    RetrieverAgent (LangGraph)
    - Input:  UserQuery
    - Output: PaperCorpus (query_id + papers[])
    - Implementation: delegates to service layer: app.services.pubmed.service.search_pubmed
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(RetrieverState)
        g.add_node("retrieve_pubmed", self.node_retrieve_pubmed)

        g.set_entry_point("retrieve_pubmed")
        g.add_edge("retrieve_pubmed", END)
        return g.compile()

    def run(self, user_query: UserQuery) -> PaperCorpus:
        state: RetrieverState = {"user_query": user_query}
        final_state = self.graph.invoke(state)

        if final_state.get("error"):
            # Orchestrator에서 잡아서 처리할 수도 있지만,
            # Retriever 단에서 명확히 실패를 드러내는 편이 디버깅에 유리합니다.
            raise RuntimeError(final_state["error"])

        return final_state["paper_corpus"]

    # -------------------------
    # LangGraph node
    # -------------------------
    def node_retrieve_pubmed(self, state: RetrieverState) -> RetrieverState:
        uq = state.get("user_query")
        if uq is None:
            state["error"] = "RetrieverState.user_query is missing."
            return state

        try:
            # Service layer 호출: query string 구성 + PMID 검색 + MEDLINE fetch + parse + PaperCorpus 생성
            paper_corpus = search_pubmed(uq)
            state["paper_corpus"] = paper_corpus
            return state
        except Exception as e:
            state["error"] = f"PubMed retrieval failed: {e}"
            return state
