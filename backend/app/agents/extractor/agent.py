# app/agents/extractor/agent.py

from __future__ import annotations
from typing import List

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
    - Preserve LLM semantics (no enum coercion)
    - Assemble KnowledgeChunk objects for vector DB ingestion
    """

    # def __init__(self, min_confidence: float = 0.0):
    #     self.min_confidence = min_confidence
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

    # 논문에서 중요정보 추출, KnowledgeChunk 생성
    def run(self, corpus: PaperCorpus) -> List[KnowledgeChunk]:
        chunks: List[KnowledgeChunk] = []

        for paper in corpus.papers:
            # =========================
            # STEP 1: abstract claim extraction
            # =========================
            extracted_claims = self._extract_claims(paper)

            outcome_claims = []

            for claim in extracted_claims:
                # (1) Claim filtering
                if self.enable_claim_filtering:
                    filter_result = self.claim_filter.filter(
                        claim=claim.claim,
                        section="abstract",
                    )

                    print(
                        f"[CLAIM FILTER] decision={filter_result['decision']} | "
                        f"reason={filter_result.get('reason')} | "
                        f"claim=\"{claim.claim}\""
                    )

                    if filter_result["decision"] == "discard":
                        continue

                # (2) Claim type classification
                claim_type = self.claim_type_classifier.classify(claim.claim)
                print(f"[CLAIM TYPE] {claim_type} | claim=\"{claim.claim}\"")

                if claim_type != "outcome":
                    continue

                outcome_claims.append(claim)

            # =========================
            # STEP 2: 정상 경로 (abstract outcome 있음)
            # =========================
            if outcome_claims:
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
            # STEP 3: 2단계-1 fallback
            # abstract에 outcome claim이 없을 때만 실행
            # =========================
            print("[FALLBACK] No outcome claim in abstract → selecting outcome sentences")

            if not paper.fulltext_sentences:
                continue

            # (3-1) 섹션 필터링
            candidate_sentences = self._filter_fulltext_by_section(
                paper.fulltext_sentences
            )

            if not candidate_sentences:
                print("[FALLBACK] No candidate sentences after section filtering")
                continue

            selected_sentence_ids = self.outcome_sentence_selector.select(
                candidate_sentences
            )

            if not selected_sentence_ids:
                print("[FALLBACK] No outcome sentences selected")
                continue

            selected_sentences = [
                s for s in candidate_sentences
                if s.sentence_id in selected_sentence_ids
            ]

            print(
                "[FALLBACK] Building conservative outcome claim from sentences:",
                selected_sentence_ids
            )

            fallback_claim = self.outcome_claim_builder.build(
                selected_sentences
            )

            if not fallback_claim:
                print("[FALLBACK] Failed to build outcome claim")
                continue

            # ===== 기존 파이프라인 재사용 =====

            # claim filtering (fulltext)
            if self.enable_claim_filtering:
                filter_result = self.claim_filter.filter(
                    claim=fallback_claim.claim,
                    section="fulltext",
                )
                if filter_result["decision"] == "discard":
                    continue

            # claim type check
            claim_type = self.claim_type_classifier.classify(
                fallback_claim.claim
            )

            print(f"[FALLBACK CLAIM TYPE] {claim_type}")

            if claim_type != "outcome":
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


        return chunks


    # ChromaDB에 생성한 KnowledgeChunk 저장
    def run_and_store(self, corpus: PaperCorpus) -> List[KnowledgeChunk]:
        """
        Execute extraction and persist resulting KnowledgeChunks into ChromaDB.
        """
        chunks = self.run(corpus)

        if chunks:
            try:
                add_chunks_to_chromadb(chunks)
            except Exception as e:
                print("[Extractor Agent] Failed to store chunks:", e)

        return chunks

    # ---------- Step 1: Claim extraction ----------
    def _filter_fulltext_by_section(self, sentences):
        return [
            s for s in sentences
            if s.section in {"results", "discussion", "conclusion"}
               and len(s.text) < 500
        ]


    def _extract_claims(self, paper: Paper) -> List[ExtractedClaim]:
        """
        LLM returns a SINGLE structured claim object.
        We wrap it into a list for uniform downstream handling.
        """

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

        prompt = claim_extraction_prompt(sentence_payload)
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
        """
        Section-agnostic Evidence Extractor
        """

        sentences = []

        # 1️⃣ fulltext가 있으면 최우선
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

        # 2️⃣ fallback: abstract라도 사용
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

        # section 정보 재결합
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


    # ---------- KnowledgeChunk assembly ----------

    def _assemble_chunk(
        self,
        paper: Paper,
        extracted: ExtractedClaim,
        idx: int,
        evidence_spans: List[dict],
    ) -> KnowledgeChunk:

        # chunk_id = f"{paper.pmid}_claim_{idx}"
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

            # core semantic fields
            claim=extracted.claim,
            target=extracted.effect.target_outcome if extracted.effect else None,
            disease=None,

            # LLM-native interpretations
            stance=extracted.stance.model_dump() if extracted.stance else None,
            effect=extracted.effect.model_dump() if extracted.effect else None,
            evidence_level=extracted.evidence_level,
            confidence=extracted.confidence,

            chunk_type="claim",
            metadata=metadata,
        )