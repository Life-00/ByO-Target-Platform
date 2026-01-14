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

TOOL_SYSTEM = """You are a retrieval planner that orchestrates tools.

Hard rules:
- expand_query MUST be called exactly once and before any search.
- search_pmids MUST be called before fetch_and_parse.
- fetch_and_parse MUST be called before rank_semantic.
- finalize MUST be called exactly once to terminate execution.
- Do NOT repeat the same tool call with identical arguments.

Strategy:
- Use rank_semantic to achieve sufficient precision when possible.
- Call llm_filter ONLY if ranking precision is insufficient.
- If no further improvement is possible, call finalize with the best available papers.

You do NOT answer biomedical questions.
You ONLY decide which tool to call next.

Return control by calling tools until finalize is called.
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
                parameters={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                },
                handler=self._handle_expand,
            ),
            "search_pmids": ToolSpec(
                name="search_pmids",
                description="Search PMIDs for the expanded queries.",
                parameters={
                    "type": "object",
                    "properties": {"retmax": {"type": "integer", "minimum": 1}},
                    "additionalProperties": False
                },
                handler=self._handle_search_pmids,
            ),
            "fetch_and_parse": ToolSpec(
                name="fetch_and_parse",
                description="Fetch MEDLINE records for PMIDs and parse to Paper objects.",
                parameters={"type": "object", "properties": {}, "additionalProperties": False},
                handler=self._handle_fetch,
            ),
            "rank_semantic": ToolSpec(
                name="rank_semantic",
                description="Semantic rank papers and pick top_n (auto knee-cutoff if enabled).",
                parameters={
                    "type": "object",
                    "properties": {"top_n": {"type": "integer", "minimum": 1}},
                    "additionalProperties": False
                },
                handler=self._handle_rank,
            ),
            "llm_filter": ToolSpec(
                name="llm_filter",
                description="LLM-based paper filtering. Optional; use when precision is needed.",
                parameters={"type": "object", "properties": {},
                            "additionalProperties": False},
                handler=self._handle_filter,
            ),
            "finalize": ToolSpec(
                name="finalize",
                description="Return the final PaperCorpus once ranking/filtering is done.",
                parameters={"type": "object", "properties": {},
                            "additionalProperties": False},
                handler=self._handle_finalize,
            ),
        }

    def run(self, uq: UserQuery) -> PaperCorpus:
        ctx = {"uq": uq, "artifacts": {}, "_called": set()}
        messages = [
            {"role": "system", "content": TOOL_SYSTEM},
            {"role": "user", "content": json.dumps(uq.model_dump(), ensure_ascii=False)},
        ]

        # 무한 루프 방지
        max_steps = 20
        no_tool_limit = 3
        no_tool_count = 0

        for _step in range(max_steps):
            resp = llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=messages,
                tools=[t.as_openai_tool() for t in self.tools.values()],
                tool_choice="auto",
                temperature=0,
            )
            msg = resp.choices[0].message

            if not msg.tool_calls:
                no_tool_count += 1
                messages.append({"role": "assistant", "content": msg.content or ""})
                if no_tool_count >= no_tool_limit:
                    raise RuntimeError("Planner produced no tool calls repeatedly (stuck).")
                continue

            no_tool_count = 0

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": msg.tool_calls,
                }
            )

            for tc in msg.tool_calls:
                name = tc.function.name
                # 툴 이름 중복 방지
                if name in {"expand_query", "search_pmids", "fetch_and_parse", "finalize"}:
                    if name in ctx["_called"]:
                        raise RuntimeError(f"Tool '{name}' called more than once.")
                    ctx["_called"].add(name)
                spec = self.tools.get(name)
                # json 오인 방지
                if spec is None:
                    raise RuntimeError(f"Unknown tool requested by planner: {name}")
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                result = spec.handler(args, ctx)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
                if name == "finalize":
                    return PaperCorpus(**result["paper_corpus"])

        raise RuntimeError("Exceeded max_steps without finalize.")
    # --- Tool handlers ---
    def _handle_expand(self, _args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        expanded = self.expander.expand(ctx["uq"])
        ctx["artifacts"]["expanded_queries"] = expanded
        return {"expanded_queries": expanded}

    def _handle_search_pmids(self, args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        retmax = args.get("retmax")
        eqs = ctx["artifacts"].get("expanded_queries") or self.expander.expand(ctx["uq"])
        pmids_by_q, prov = self.fetcher.collect_pmids(eqs, retmax=retmax)
        ctx["artifacts"]["expanded_queries"] = eqs
        ctx["artifacts"]["pmid_prov"] = prov
        return {"pmids_by_query": pmids_by_q, "pmid_provenance": prov}

    def _handle_fetch(self, _args, ctx):
        if "expanded_queries" not in ctx["artifacts"] or "pmid_prov" not in ctx["artifacts"]:
            raise RuntimeError("fetch_and_parse requires expanded_queries and pmid_prov. Call search_pmids first.")
        eqs = ctx["artifacts"]["expanded_queries"]
        prov = ctx["artifacts"]["pmid_prov"]
        papers = self.fetcher.fetch_and_parse(eqs, prov)
        ctx["artifacts"]["papers_raw"] = papers

        preview = [
            {
                "pmid": p.pmid,
                "title": p.title,
                "year": p.year,
                "journal": p.journal,
                "retrieval_reason": getattr(p, "retrieval_reason", None),
            }
            for p in papers[:50]
        ]
        return {"count": len(papers), "preview": preview}

    def _handle_rank(self, args, ctx):
        if "papers_raw" not in ctx["artifacts"]:
            raise RuntimeError("rank_semantic requires papers_raw. Call fetch_and_parse first.")

        top_n = args.get("top_n", self.semantic_top_n)
        uq = ctx["uq"]
        qtext = " ".join([t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t])

        papers_raw = ctx["artifacts"]["papers_raw"]
        papers, scores = self.ranker.rank(qtext, papers_raw, top_n=top_n)

        ctx["artifacts"]["papers_ranked"] = papers
        ctx["artifacts"]["scores"] = scores
        return {"top_n": len(papers), "pmids": [p.pmid for p in papers], "confidence_hint": "high" | "low"}

    def _handle_filter(self, _args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        papers = ctx["artifacts"].get("papers_ranked") or ctx["artifacts"].get("papers_raw") or []
        if not papers:
            return {"kept_pmids": [], "meta": {}, "skipped": True}
        if not self.use_llm_filter:
            return {"kept_pmids": [p.pmid for p in papers], "meta": {}, "skipped": True}
        kept, meta = self.filter.filter(ctx["uq"], papers)
        ctx["artifacts"]["papers_filtered"] = kept
        return {"kept_pmids": [p.pmid for p in kept], "meta": meta, "skipped": False}

    def _handle_finalize(self, _args: Dict[str, Any], ctx) -> Dict[str, Any]:
        papers = (
                ctx["artifacts"].get("papers_filtered")
                or ctx["artifacts"].get("papers_ranked")
                or ctx["artifacts"].get("papers_raw")
                or []
        )
        corpus = PaperCorpus(query_id=ctx["uq"].query_id, papers=papers)
        ctx["artifacts"]["paper_corpus"] = corpus
        return {"paper_corpus": corpus.model_dump()}