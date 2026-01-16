# app/agents/extractor/agent.py

from __future__ import annotations
from typing import List, Optional  # Optional 추가
import time

from app.agents.extractor.prompts import claim_extraction_prompt, evidence_extraction_prompt
from app.agents.extractor.parser import (
    parse_json_response,
    ExtractedClaim,
    EvidenceExtractionResult,
)
from app.agents.extractor.claim_filter import ClaimFilter
from app.agents.extractor.claim_type_classifier import ClaimTypeClassifier
from app.agents.extractor.outcome_sentence_selector import OutcomeSentenceSelector
from app.agents.extractor.outcome_claim_builder import ConservativeOutcomeClaimBuilder

from app.schemas.retrieval import PaperCorpus, Paper
from app.schemas.knowledge import KnowledgeChunk
from app.core.llm import call_llm

from app.service.chromadb.ingest_chunk import add_chunks_to_chromadb

class ExtractorAgent:
    """
    LLM-only Extractor Agent
    Responsibilities:
    - Extract structured claims from abstract sentences
    - Preserve LLM semantics
    - Assemble KnowledgeChunk objects for vector DB ingestion
    """

    def __init__(
            self,
            enable_claim_filtering: bool = True,
            enable_claim_type_filtering: bool = True,
            min_confidence: float = 0.0,
    ):
        self.min_confidence = min_confidence
        self.enable_claim_filtering = enable_claim_filtering
        self.enable_claim_type_filtering = enable_claim_type_filtering

        self.claim_filter = ClaimFilter()
        self.claim_type_classifier = ClaimTypeClassifier()

        self.outcome_sentence_selector = OutcomeSentenceSelector()
        self.outcome_claim_builder = ConservativeOutcomeClaimBuilder()

    # ✅ instruction 파라미터 추가 (기존 코드 호환성 유지)
    def run(self, corpus: PaperCorpus, instruction: Optional[str] = None) -> List[KnowledgeChunk]:
        chunks: List[KnowledgeChunk] = []
        
        # tqdm 제거됨 -> 로그 출력으로 대체
        total_papers = len(corpus.papers)
        print(f"[ExtractorAgent] Start processing {total_papers} papers...")

        for p_idx, paper in enumerate(corpus.papers):
            print(f"[ExtractorAgent] Processing paper {p_idx + 1}/{total_papers}: {paper.pmid or 'Unknown ID'}")

            time.sleep(2)
            # =========================
            # STEP 1: abstract claim extraction
            # =========================
            # ✅ instruction 전달
            extracted_claims = self._extract_claims(paper, instruction)

            outcome_claims = []

            for claim in extracted_claims:
                # (1) Claim filtering
                if self.enable_claim_filtering:
                    filter_result = self.claim_filter.filter(
                        claim=claim.claim,
                        section="abstract",
                    )
                    
                    # 디버그 로그
                    # print(
                    #     f"  [FILTER] {filter_result['decision']} | "
                    #     f"reason={filter_result.get('reason')} | "
                    #     f"claim=\"{claim.claim[:50]}...\""
                    # )

                    if filter_result["decision"] == "discard":
                        continue

                # (2) Claim type classification
                claim_type = self.claim_type_classifier.classify(claim.claim)
                # print(f"  [TYPE] {claim_type} | claim=\"{claim.claim[:50]}...\"")

                if self.enable_claim_type_filtering and claim_type != "outcome":
                    continue

                outcome_claims.append(claim)

            # =========================
            # STEP 2: 정상 경로 (abstract outcome 있음)
            # =========================
            if outcome_claims:
                print(f"  -> Found {len(outcome_claims)} outcome claims in Abstract.")
                for idx, claim in enumerate(outcome_claims):
                    evidence = self._extract_evidence(paper, claim)

                    chunk = self._assemble_chunk(
                        paper=paper,
                        extracted=claim,
                        idx=idx,
                        evidence_spans=evidence,
                    )
                    chunks.append(chunk)

                continue  # 👉 다음 paper로

            # =========================
            # STEP 3: Fallback (Abstract 실패 시 Fulltext 사용)
            # =========================
            print("  -> [FALLBACK] No outcome claim in abstract. Attempting fulltext search...")

            if not paper.fulltext_sentences:
                print("  -> [FALLBACK] No fulltext sentences available. Skipping.")
                continue

            # (3-1) 섹션 필터링
            candidate_sentences = self._filter_fulltext_by_section(
                paper.fulltext_sentences
            )

            if not candidate_sentences:
                print("  -> [FALLBACK] No candidate sentences after section filtering.")
                continue

            selected_sentence_ids = self.outcome_sentence_selector.select(
                candidate_sentences
            )

            if not selected_sentence_ids:
                print("  -> [FALLBACK] No outcome sentences selected by LLM.")
                continue

            selected_sentences = [
                s for s in candidate_sentences
                if s.sentence_id in selected_sentence_ids
            ]

            print(
                f"  -> [FALLBACK] Building claim from {len(selected_sentence_ids)} sentences."
            )

            fallback_claim = self.outcome_claim_builder.build(
                selected_sentences
            )

            if not fallback_claim:
                print("  -> [FALLBACK] Failed to build outcome claim.")
                continue

            # ===== 기존 파이프라인 재사용 =====

            # claim filtering (fulltext)
            if self.enable_claim_filtering:
                filter_result = self.claim_filter.filter(
                    claim=fallback_claim.claim,
                    section="fulltext",
                )
                if filter_result["decision"] == "discard":
                    print("  -> [FALLBACK] Generated claim discarded by filter.")
                    continue

            # claim type check
            claim_type = self.claim_type_classifier.classify(
                fallback_claim.claim
            )

            if self.enable_claim_type_filtering and claim_type != "outcome":
                print(f"  -> [FALLBACK] Generated claim type is '{claim_type}', not outcome.")
                continue

            # evidence extraction
            evidence = self._extract_evidence(paper, fallback_claim)

            chunk = self._assemble_chunk(
                paper=paper,
                extracted=fallback_claim,
                idx=0,
                evidence_spans=evidence,
            )

            chunks.append(chunk)
            print("  -> [FALLBACK] Successfully created 1 chunk.")

        return chunks

    # 저장까지 수행하는 함수
    def run_and_store(self, corpus: PaperCorpus, instruction: Optional[str] = None) -> List[KnowledgeChunk]:
        chunks = self.run(corpus, instruction=instruction)

        if chunks:
            try:
                print(f"[ExtractorAgent] Storing {len(chunks)} chunks to ChromaDB...")
                add_chunks_to_chromadb(chunks)
                print("[ExtractorAgent] Storage complete.")
            except Exception as e:
                print("[ExtractorAgent] Failed to store chunks:", e)

        return chunks

    def _filter_fulltext_by_section(self, sentences):
        # 섹션 이름이 results, discussion, conclusion 포함된 경우만 필터링
        return [
            s for s in sentences
            if s.section and any(k in s.section.lower() for k in ["result", "discussion", "conclusion"])
               and len(s.text) < 500
        ]

    # ✅ instruction 파라미터 추가
    def _extract_claims(self, paper: Paper, instruction: str = None) -> List[ExtractedClaim]:
        sentence_payload = [
            {
                "sentence_id": s.sentence_id,
                "text": s.text
            }
            for s in (paper.abstract_sentences or [])
            if s.text
        ]

        if not sentence_payload:
            return []

        # ✅ 프롬프트에 instruction 전달 (prompts.py 수정 필요 없음)
        prompt = claim_extraction_prompt(sentence_payload, focus_instruction=instruction)
        response = call_llm(prompt)

        try:
            data = parse_json_response(response)
            extracted = ExtractedClaim(**data)
            return [extracted]
        except Exception as e:
            print("[Claim Extractor] parse failed:", e)
            return []

    # ---------- Phase 2: Evidence Extraction ----------
    def _extract_evidence(
            self,
            paper: Paper,
            claim: ExtractedClaim,
    ) -> List[dict]:
        sentences = []

        if paper.fulltext_sentences:
            for s in paper.fulltext_sentences:
                if s.text:
                    sentences.append(
                        {
                            "sentence_id": s.sentence_id,
                            "section": s.section or "unknown",
                            "text": s.text,
                        }
                    )
        elif paper.abstract_sentences:
            for s in paper.abstract_sentences:
                if s.text:
                    sentences.append(
                        {
                            "sentence_id": s.sentence_id,
                            "section": "abstract",
                            "text": s.text,
                        }
                    )

        if not sentences:
            return []

        prompt = evidence_extraction_prompt(
            claim=claim.claim,
            sentences=sentences,
        )
        response = call_llm(prompt)

        try:
            data = parse_json_response(response)
            parsed = EvidenceExtractionResult(**data)
        except Exception as e:
            print("[Evidence Extractor] parse failed:", e)
            return []

        sentence_section_map = {
            s["sentence_id"]: s["section"] for s in sentences
        }

        return [
            {
                "sentence_id": ev.sentence_id,
                "section": sentence_section_map.get(ev.sentence_id),
                "role": ev.role,
            }
            for ev in parsed.evidence_spans
        ]

    def _assemble_chunk(
        self,
        paper: Paper,
        extracted: ExtractedClaim,
        idx: int,
        evidence_spans: List[dict],
    ) -> KnowledgeChunk:

        source_id = paper.pmid or paper.source_id or "unknown"
        chunk_id = f"{source_id}_claim_{idx}"

        metadata = {
            "paper_title": paper.title,
            "journal": paper.journal,
            "year": paper.year,
            "retrieval_reason": paper.retrieval_reason,
            "salience": (
                extracted.salience.model_dump()
                if extracted.salience
                else None
            ),
            "notes": extracted.notes,
            "evidence_spans": evidence_spans,
        }

        return KnowledgeChunk(
            chunk_id=chunk_id,
            query_id=paper.query_id,
            pmid=paper.pmid,

            claim=extracted.claim,
            target=extracted.effect.target_outcome if extracted.effect else None,
            disease=None,

            stance=extracted.stance.model_dump() if extracted.stance else None,
            effect=extracted.effect.model_dump() if extracted.effect else None,
            evidence_level=extracted.evidence_level,
            confidence=extracted.confidence,

            chunk_type="claim",
            metadata=metadata,
        )