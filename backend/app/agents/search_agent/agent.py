"""
Search Agent Implementation (Orchestrator)
최적화 사항: 
1. 다중 쿼리 확장(Expansion) 및 병렬 검색 적용
2. Knee-cutoff을 통한 동적 결과 정제
3. 검색 실패 시 재시도(Retry) 및 Fallback 로직 강화
"""

import logging
import json
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.search_agent.schemas import SearchAgentRequest, SearchAgentResponse, PaperInfo
from app.agents.search_agent.prompt import (
    SEARCH_QUERY_GENERATION_PROMPT,
    RELEVANCE_EVALUATION_PROMPT,
    REQUESTED_COUNT_EXTRACTION_PROMPT,
    SEARCH_QUERY_EXPANSION_PROMPT,
    DEFAULT_MAX_RESULTS,
    DEFAULT_EXPANSION_COUNT,
)
from app.agents.search_agent.europe_pmc_search import search_biorxiv, search_biorxiv_api
from app.agents.search_agent.pdf_download import download_pdfs
from app.services.llm_service import get_llm_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class SearchAgent(BaseAgent):
    def __init__(self, db: AsyncSession = None):
        super().__init__()
        self.agent_type = "search_agent"
        self.llm_service = get_llm_service()
        self.db = db
        self.uploads_dir = Path("/app/uploads")
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, request: SearchAgentRequest) -> SearchAgentResponse:
        search_query_str = request.content[:100]
        try:
            logger.info(f"[SearchAgent] Starting search: {request.content[:50]}...")

            # Step 0: 사용자 요청 개수 추출
            actual_max_results = await self._extract_requested_count(request.content)

            # Step 0.5: 기다운로드 문서 제외 리스트 확보
            existing_preprint_ids = set()
            if request.selected_documents:
                for doc in request.selected_documents:
                    candidate = str(doc.get("external_id") or doc.get("doi") or doc.get("preprint_id") or "").strip()
                    if candidate: existing_preprint_ids.add(candidate)

            best_filtered: List[PaperInfo] = []
            best_merged: List[Dict[str, Any]] = []

            for attempt in range(request.max_query_retries + 1):
                # Step 1: 베이스 쿼리 생성 및 다중 쿼리 확장 (LLM)
                base_query = await self._generate_search_query(request.content, request.analysis_goal)
                expanded_queries = await self._expand_search_queries(base_query, DEFAULT_EXPANSION_COUNT)
                search_query_str = "; ".join(expanded_queries)
                logger.info(f"[SearchAgent] Query attempt {attempt+1}/{request.max_query_retries+1} for: {expanded_queries}")

                # Step 2: Europe PMC 병렬 검색 + 재시도 로직
                search_tasks = [
                    self._search_with_retry(q, actual_max_results * 4)
                    for q in expanded_queries
                ]
                search_results = await asyncio.gather(*search_tasks)

                # 결과 병합 및 중복 제거
                merged_papers = self._merge_papers(search_results, existing_preprint_ids)
                if merged_papers:
                    best_merged = merged_papers
                logger.info(f"[SearchAgent] Total unique candidates found: {len(merged_papers)}")

                # Europe PMC 결과 없음 -> bioRxiv API fallback
                if not merged_papers:
                    if attempt < request.max_query_retries:
                        logger.info("[SearchAgent] No papers found; regenerating queries and retrying...")
                        continue
                    logger.info("[SearchAgent] Europe PMC returned no results; trying bioRxiv API fallback")
                    merged_papers = await search_biorxiv_api(request.content, actual_max_results * 2)
                    best_merged = merged_papers

                # Step 3: 병렬 적합성 필터링 및 Knee-cutoff
                filtered_papers = await self._filter_by_relevance_parallel(
                    merged_papers,
                    request.content,
                    request.analysis_goal,
                    request.min_relevance_score,
                    actual_max_results,
                    existing_preprint_ids
                )
                if filtered_papers:
                    best_filtered = filtered_papers

                # 재검색 조건: 필터 결과가 없으면 쿼리 재생성 후 재검색
                if attempt < request.max_query_retries and not filtered_papers:
                    logger.info("[SearchAgent] No relevant papers after filtering; regenerating queries and retrying...")
                    continue

                # 충분한 결과 확보 -> 루프 종료
                filtered_papers = filtered_papers or best_filtered
                merged_papers = merged_papers or best_merged
                break

            # Step 4: PDF 다운로드 및 DB 등록
            download_results = await download_pdfs(
                filtered_papers,
                request.session_id,
                request.user_id,
                self.uploads_dir,
                self.db
            )

            # Europe PMC에서 본문을 못 내려받은 경우 bioRxiv API로 추가 재검색/재다운로드
            if not download_results["paths"]:
                logger.info("[SearchAgent] No fulltext downloaded; falling back to bioRxiv API for fulltext-available papers.")
                biorxiv_candidates = await search_biorxiv_api(request.content, actual_max_results * 2)
                if biorxiv_candidates:
                    best_merged = biorxiv_candidates
                    bio_filtered = await self._filter_by_relevance_parallel(
                        biorxiv_candidates,
                        request.content,
                        request.analysis_goal,
                        request.min_relevance_score,
                        actual_max_results,
                        existing_preprint_ids,
                    )
                    if bio_filtered:
                        filtered_papers = bio_filtered
                        download_results = await download_pdfs(
                            bio_filtered,
                            request.session_id,
                            request.user_id,
                            self.uploads_dir,
                            self.db,
                        )

            return SearchAgentResponse(
                success=True,
                search_query=search_query_str,
                papers_found=len(best_merged or filtered_papers),
                papers_filtered=len(filtered_papers),
                papers_downloaded=len(download_results['paths']),
                papers=filtered_papers,
                download_paths=download_results['paths'],
                document_ids=download_results['document_ids'],
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "requested_count": actual_max_results
                }
            )

        except Exception as e:
            logger.error(f"[SearchAgent] Critical Error: {str(e)}")
            return SearchAgentResponse(
                success=False,
                search_query=search_query_str,
                papers_found=0,
                papers_filtered=0,
                papers_downloaded=0,
                papers=[],
                download_paths=[],
                document_ids=[],
                error=str(e),
                metadata={"timestamp": datetime.now().isoformat()}
            )

    def _sanitize_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        필수 필드를 기본값으로 채워 downstream 검증/저장을 안전하게 합니다.
        """
        p = dict(paper or {})
        p.setdefault("title", "")
        p.setdefault("abstract", "")
        p.setdefault("authors", [])
        p.setdefault("preprint_id", p.get("preprint_id") or p.get("doi") or "")
        p.setdefault("doi", p.get("doi") or p.get("preprint_id") or "")
        p.setdefault("pmcid", p.get("pmcid") or "")
        p.setdefault("arxiv_id", p.get("arxiv_id") or "")
        p.setdefault("source", p.get("source") or "unknown")
        p.setdefault("pdf_url", p.get("pdf_url") or "")
        p.setdefault("fulltext_xml_url", p.get("fulltext_xml_url") or "")
        p.setdefault("published_date", p.get("published_date") or "")
        return p

    async def _evaluate_single_paper(self, paper: Dict[str, Any], content: str, goal: Optional[str]) -> Optional[PaperInfo]:
        paper = self._sanitize_paper(paper)
        try:
            prompt = RELEVANCE_EVALUATION_PROMPT.format(
                content=content,
                analysis_goal=goal or "General research",
                title=paper["title"],
                abstract=paper["abstract"][:1000]
            )
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert at evaluating research paper relevance.",
                temperature=0.0,
                max_tokens=200
            )
            raw = response["content"].strip()
            # 코드블록 래핑 제거
            if raw.startswith("```"):
                raw = raw.strip("` \n")
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            # JSON이 문장과 섞여 있을 때 첫 번째 객체만 파싱
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            target = match.group(0) if match else raw
            result = json.loads(target)
            score = float(result.get("relevance_score", 0.0))

            return PaperInfo(
                title=paper["title"],
                authors=paper["authors"],
                abstract=paper["abstract"],
                preprint_id=paper.get("preprint_id") or "",
                doi=paper.get("doi") or "",
                pmcid=paper.get("pmcid") or "",
                arxiv_id=paper.get("arxiv_id") or "",
                source=paper.get("source") or "biorxiv",
                pdf_url=paper["pdf_url"],
                fulltext_xml_url=paper.get("fulltext_xml_url") or "",
                published_date=paper["published_date"],
                relevance_score=score
            )
        except Exception as e:
            logger.warning(f"Evaluation failed: {e}")
            # 파싱 실패 시 낮은 점수로라도 반환하여 후속 fallback(top-N)에서 활용
            return PaperInfo(
                title=paper.get("title", ""),
                authors=paper.get("authors", []),
                abstract=paper.get("abstract", ""),
                preprint_id=paper.get("preprint_id") or "",
                doi=paper.get("doi") or "",
                pmcid=paper.get("pmcid") or "",
                arxiv_id=paper.get("arxiv_id") or "",
                source=paper.get("source") or "biorxiv",
                pdf_url=paper.get("pdf_url") or "",
                fulltext_xml_url=paper.get("fulltext_xml_url") or "",
                published_date=paper.get("published_date") or "",
                relevance_score=0.0
            )

    async def _filter_by_relevance_parallel(
        self, papers, content, goal, min_score, max_results, existing_ids
    ) -> List[PaperInfo]:
        tasks = [self._evaluate_single_paper(p, content, goal) for p in papers]
        results = await asyncio.gather(*tasks)
        
        all_scored = [p for p in results if p is not None]
        scored_papers = [p for p in all_scored if p.relevance_score >= min_score]
        scored_papers.sort(key=lambda x: x.relevance_score, reverse=True)

        # Knee-cutoff 적용
        final_list = []
        if scored_papers:
            final_list.append(scored_papers[0])
            for i in range(1, len(scored_papers)):
                if (scored_papers[i-1].relevance_score - scored_papers[i].relevance_score) > 0.3:
                    logger.info(f"[SearchAgent] Knee-point detected at index {i}")
                    break
                final_list.append(scored_papers[i])

        # Fallback: 결과가 너무 적으면 점수순으로 강제 반환
        if not final_list and all_scored:
            all_scored.sort(key=lambda x: x.relevance_score, reverse=True)
            final_list = all_scored[:max_results]

        return final_list[:max_results]

    async def _extract_requested_count(self, content: str) -> int:
        try:
            prompt = REQUESTED_COUNT_EXTRACTION_PROMPT.format(content=content)
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert at understanding user requests.",
                temperature=0.1,
                max_tokens=50
            )
            result = json.loads(response["content"].strip())
            return max(1, min(20, int(result.get("requested_count", DEFAULT_MAX_RESULTS))))
        except Exception:
            return DEFAULT_MAX_RESULTS

    async def _generate_search_query(self, content: str, analysis_goal: Optional[str]) -> str:
        try:
            prompt = SEARCH_QUERY_GENERATION_PROMPT.format(
                content=content,
                analysis_goal=analysis_goal or "General research"
            )
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert research assistant.",
                temperature=0.3,
                max_tokens=100
            )
            return response["content"].strip()
        except Exception:
            return content[:100]

    async def _expand_search_queries(self, base_query: str, count: int) -> List[str]:
        try:
            prompt = SEARCH_QUERY_EXPANSION_PROMPT.format(base_query=base_query, count=count)
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert search query expander.",
                temperature=0.4,
                max_tokens=200
            )
            raw = response["content"].strip()
            if raw.startswith("```"):
                raw = raw.strip("` \n")
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            queries = json.loads(raw)
            if not isinstance(queries, list):
                return [base_query]
            cleaned = []
            for q in queries:
                if isinstance(q, str):
                    cleaned.append(q.replace('"', " ").strip())
            cleaned = [q for q in cleaned if q]
            if base_query not in cleaned:
                cleaned.insert(0, base_query)
            return list(dict.fromkeys(cleaned))
        except Exception as e:
            logger.warning(f"Expansion failed: {e}")
            return [base_query]

    async def _search_with_retry(self, query: str, max_results: int, retries: int = 2, min_results: int = 2) -> List[Dict[str, Any]]:
        """
        검색 재시도: 결과가 min_results 미만이면 최대 retries까지 시도 (page size 점진 확대)
        """
        results: List[Dict[str, Any]] = []
        current_max = max_results
        for attempt in range(retries + 1):
            results = await search_biorxiv(query, current_max)
            if len(results) >= min_results:
                break
            current_max = min(current_max * 2, 50)  # Europe PMC pageSize 상한 고려
            logger.info(f"[SearchAgent] Search retry {attempt+1}/{retries} for query: {query} (current_max={current_max}, got={len(results)})")
        return results

    def _merge_papers(self, search_results: List[List[Dict[str, Any]]], existing_ids: set) -> List[Dict[str, Any]]:
        merged = {}
        for papers in search_results:
            for paper in papers:
                paper = self._sanitize_paper(paper)
                if not paper["title"]:
                    continue
                pid = paper.get("preprint_id") or paper.get("doi")
                if pid and pid not in existing_ids and pid not in merged:
                    merged[pid] = paper
        return list(merged.values())
