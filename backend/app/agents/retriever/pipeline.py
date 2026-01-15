from __future__ import annotations
import time
import json

from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus

from app.agents.retriever.query_expander import QueryExpander
from app.agents.retriever.pubmed_fetcher import PubMedFetcher
from app.agents.retriever.semantic_ranker import SemanticRanker
from app.agents.retriever.paper_filter import PaperFilter


class RetrieverPipeline:
    def __init__(
            self,
            use_llm_expand: bool = True,
            use_llm_filter: bool = True,
            default_retmax: int = 300,
            semantic_top_n: int = 200,
            llm_keep_eval_n: int = 80,
            use_knee_cutoff: bool = True,
            knee_min_k: int = 5,
            knee_max_k: int | None = None,
    ):
        self.expander = QueryExpander(use_llm=use_llm_expand)
        # PMC 우선 검색을 위해 업데이트된 PubMedFetcher 사용
        self.fetcher = PubMedFetcher(default_retmax=default_retmax)
        self.ranker = SemanticRanker(
            use_knee_cutoff=use_knee_cutoff,
            knee_min_k=knee_min_k,
            knee_max_k=knee_max_k or semantic_top_n,
        )
        self.filter = PaperFilter(keep_eval_n=llm_keep_eval_n)

        self.use_llm_filter = use_llm_filter
        self.semantic_top_n = semantic_top_n

    def run_stream(self, uq: UserQuery):
        """
        [PMC-Centric Pipeline]
        모든 검색 단계를 PMC(Full-text 확보 가능 논문) 위주로 처리합니다.
        """
        
        # 1) Query expansion
        print(f"\n[Pipeline] 검색 시작: {uq.intent}")
        yield {"type": "log", "content": "🔎 PMC 전문 데이터베이스 최적화 검색어 확장 중..."}
        expanded_queries = self.expander.expand(uq)
        print(f"[Pipeline] 확장된 검색어 {len(expanded_queries)}개 생성 완료")
        yield {"type": "log", "content": f"   👉 확장된 검색어 {len(expanded_queries)}개 생성됨"}

        # 2) Collect PMIDs (PMC 전용 DB 검색)
        retmax = None
        if getattr(uq, "constraints", None) is not None:
            retmax = getattr(uq.constraints, "max_results", None)

        print(f"[Pipeline] PMC ID 수집 시작 (목표: {retmax or self.fetcher.default_retmax}건)")
        yield {"type": "log", "content": f"📄 실물 PDF 확보 가능한 논문 수집 중... (PMC DB)"}
        
        # fetcher 내부에서 db='pmc' 및 "free full text"[Filter]를 적용합니다.
        _, pmid_prov = self.fetcher.collect_pmids(expanded_queries, retmax=retmax)
        
        print(f"[Pipeline] 총 {len(pmid_prov)}개의 유효한 PMC ID 발견")
        yield {"type": "log", "content": f"   👉 총 {len(pmid_prov)}개의 고유 PMC ID 수집 완료"}

        if not pmid_prov:
            print("[Pipeline] 검색 결과 없음. 종료.")
            yield {"type": "log", "content": "⚠️ PMC 내에 전문이 공개된 논문이 없습니다. 검색 조건을 조정해 보세요."}
            yield {"type": "result", "data": PaperCorpus(query_id=uq.query_id, papers=[])}
            return

        # 3) Fetch + parse (PMC 데이터 기준)
        print(f"[Pipeline] 논문 데이터 다운로드 및 파싱 시작 (Target: {len(pmid_prov)}건)")
        yield {"type": "log", "content": "📥 PMC 논문 정보 및 초록 다운로드 중..."}
        
        start_t = time.time()
        # fetch_and_parse 내에서 db='pmc'를 사용하여 상세 정보를 가져옵니다.
        papers_raw = self.fetcher.fetch_and_parse(expanded_queries, pmid_prov)
        
        print(f"[Pipeline] 다운로드 완료: {len(papers_raw)}건 ({time.time()-start_t:.2f}초 소요)")
        yield {"type": "log", "content": f"   👉 {len(papers_raw)}건 로드 완료"}

        # 4) Semantic rerank + topN
        qtext = " ".join(
            [t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t]
        )
        print(f"[Pipeline] 의미 기반 랭킹 계산 중 (Top-N: {self.semantic_top_n})")
        yield {"type": "log", "content": "🧠 연구 의도 기반 랭킹(Semantic Ranking) 계산 중..."}
        
        papers_topn, _scores = self.ranker.rank(qtext, papers_raw, top_n=self.semantic_top_n)
        print(f"[Pipeline] 랭킹 상위 {len(papers_topn)}건 선정")
        yield {"type": "log", "content": f"   👉 랭킹 상위 {len(papers_topn)}건 선정 완료"}

        # 5) LLM Filter (선택 사항)
        if self.use_llm_filter:
            print(f"[Pipeline] LLM 필터링 시작 (대상: {len(papers_topn)}건)")
            yield {"type": "log", "content": "🤖 LLM 적합성 평가 진행 중... (실물 분석 가치 판단)"}
            kept, _meta = self.filter.filter(uq, papers_topn)
            final_papers = kept
            print(f"[Pipeline] 필터 통과: {len(final_papers)}건")
            yield {"type": "log", "content": f"   👉 최종 {len(final_papers)}건 선정 완료"}
        else:
            final_papers = papers_topn
            print("[Pipeline] LLM 필터링 건너뜀")
            yield {"type": "log", "content": "🤖 LLM 필터링 건너뜀 (설정: OFF)"}

        # 6) Output
        print(f"[Pipeline] 모든 작업 완료. {len(final_papers)}개의 결과를 전송합니다.\n")
        yield {"type": "log", "content": "✅ 모든 작업 완료! 실물 PDF 확보를 시도합니다..."}
        
        # 최종 결과 객체 반환
        yield {"type": "result", "data": PaperCorpus(query_id=uq.query_id, papers=final_papers)}