from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import json

from app.core.llm import llm_client, DEFAULT_LLM_MODEL
from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus
from app.agents.retriever.query_expander import QueryExpander
from app.agents.retriever.pubmed_fetcher import PubMedFetcher
from app.agents.retriever.semantic_ranker import SemanticRanker
from app.agents.retriever.paper_filter import PaperFilter

TOOL_SYSTEM = """You are a retrieval planner. Pick and chain the provided tools.
- Use expand_query before searching PMIDs.
- Collect PMIDs, then fetch_and_parse.
- Use rank_semantic to sort papers.
- Use llm_filter optionally; skip if enough precision from ranking.
- Call finalize when you have the final PaperCorpus.
"""


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]

    def as_openai_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class RetrieverToolRouter:
    def __init__(
            self,
            use_llm_expand: bool = True,
            use_llm_filter: bool = True,
            default_retmax: int = 300,
            semantic_top_n: int = 200,
            llm_keep_eval_n: int = 80,
            use_knee_cutoff: bool = True,
            knee_min_k: int = 5,
            knee_max_k: Optional[int] = None,
    ):
        self.expander = QueryExpander(use_llm=use_llm_expand)
        self.fetcher = PubMedFetcher(default_retmax=default_retmax)
        self.ranker = SemanticRanker(
            use_knee_cutoff=use_knee_cutoff,
            knee_min_k=knee_min_k,
            knee_max_k=knee_max_k or semantic_top_n,
        )
        self.filter = PaperFilter(keep_eval_n=llm_keep_eval_n)
        self.use_llm_filter = use_llm_filter
        self.semantic_top_n = semantic_top_n

        self.tools: Dict[str, ToolSpec] = {
            "expand_query": ToolSpec(
                name="expand_query",
                description="Expand the user query into multiple PubMed terms.",
                parameters={"type": "object", "properties": {}},
                handler=self._handle_expand,
            ),
            "search_pmids": ToolSpec(
                name="search_pmids",
                description="Search PMIDs for the expanded queries.",
                parameters={
                    "type": "object",
                    "properties": {"retmax": {"type": "integer", "minimum": 1}},
                },
                handler=self._handle_search_pmids,
            ),
            "fetch_and_parse": ToolSpec(
                name="fetch_and_parse",
                description="Fetch MEDLINE records for PMIDs and parse to Paper objects.",
                parameters={"type": "object", "properties": {}},
                handler=self._handle_fetch,
            ),
            "rank_semantic": ToolSpec(
                name="rank_semantic",
                description="Semantic rank papers and pick top_n (auto knee-cutoff if enabled).",
                parameters={
                    "type": "object",
                    "properties": {"top_n": {"type": "integer", "minimum": 1}},
                },
                handler=self._handle_rank,
            ),
            "llm_filter": ToolSpec(
                name="llm_filter",
                description="LLM-based paper filtering. Optional; use when precision is needed.",
                parameters={"type": "object", "properties": {}},
                handler=self._handle_filter,
            ),
            "finalize": ToolSpec(
                name="finalize",
                description="Return the final PaperCorpus once ranking/filtering is done.",
                parameters={"type": "object", "properties": {}},
                handler=self._handle_finalize,
            ),
        }

    def run(self, uq: UserQuery) -> PaperCorpus:
        ctx: Dict[str, Any] = {"uq": uq}
        messages = [
            {"role": "system", "content": TOOL_SYSTEM},
            {"role": "user", "content": json.dumps(uq.model_dump(), ensure_ascii=False)},
        ]

        while True:
            resp = llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=messages,
                tools=[t.as_openai_tool() for t in self.tools.values()],
                tool_choice="auto",
                temperature=0,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                # No tool call, loop until we have a finalize
                messages.append({"role": "assistant", "content": msg.content or ""})
                continue

            for tc in msg.tool_calls:
                name = tc.function.name
                spec = self.tools[name]
                args = json.loads(tc.function.arguments or "{}")
                result = spec.handler(args, ctx)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
                if name == "finalize":
                    return result["paper_corpus"]

    # --- Tool handlers ---
    def _handle_expand(self, _args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        expanded = self.expander.expand(ctx["uq"])
        ctx["expanded_queries"] = expanded
        return {"expanded_queries": expanded}

    def _handle_search_pmids(self, args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        retmax = args.get("retmax")
        eqs = ctx.get("expanded_queries") or self.expander.expand(ctx["uq"])
        pmids_by_q, prov = self.fetcher.collect_pmids(eqs, retmax=retmax)
        ctx["expanded_queries"] = eqs
        ctx["pmid_prov"] = prov
        return {"pmids_by_query": pmids_by_q, "pmid_provenance": prov}

    def _handle_fetch(self, _args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        eqs = ctx["expanded_queries"]
        prov = ctx["pmid_prov"]
        papers = PubMedFetcher.fetch_and_parse(eqs, prov)
        ctx["papers"] = papers
        return {"papers": [p.model_dump() for p in papers]}

    def _handle_rank(self, args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        top_n = args.get("top_n", self.semantic_top_n)
        uq = ctx["uq"]
        qtext = " ".join([t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t])
        papers, scores = self.ranker.rank(qtext, ctx["papers"], top_n=top_n)
        ctx["papers_ranked"] = papers
        ctx["scores"] = scores
        return {"top_n": len(papers), "pmids": [p.pmid for p in papers]}

    def _handle_filter(self, _args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        papers = ctx.get("papers_ranked") or ctx["papers"]
        if not self.use_llm_filter:
            return {"kept_pmids": [p.pmid for p in papers], "meta": {}, "skipped": True}
        kept, meta = self.filter.filter(ctx["uq"], papers)
        ctx["papers_filtered"] = kept
        return {"kept_pmids": [p.pmid for p in kept], "meta": meta, "skipped": False}

    def _handle_finalize(self, _args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        papers = ctx.get("papers_filtered") or ctx.get("papers_ranked") or ctx["papers"]
        corpus = PaperCorpus(query_id=ctx["uq"].query_id, papers=papers)
        ctx["paper_corpus"] = corpus
        return {"paper_corpus": corpus.model_dump()}