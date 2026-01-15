# app/agents/extractor/agent.py

from __future__ import annotations
from typing import List

from app.agents.extractor.prompts import claim_extraction_prompt, evidence_extraction_prompt
from app.agents.extractor.parser import (
    parse_json_response,
    ExtractedClaim,
    EvidenceExtractionResult,
)
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

    def __init__(self, min_confidence: float = 0.0):
        self.min_confidence = min_confidence

    # 논문에서 중요정보 추출, KnowledgeChunk 생성
    def run(self, corpus: PaperCorpus) -> List[KnowledgeChunk]:
        chunks: List[KnowledgeChunk] = []

        for paper in corpus.papers:
            extracted_claims = self._extract_claims(paper)

            for idx, claim in enumerate(extracted_claims):
                if claim.confidence is not None and claim.confidence < self.min_confidence:
                    continue

                evidence = self._extract_evidence(paper, claim)

                chunk = self._assemble_chunk(
                    paper=paper,
                    extracted=claim,
                    idx=idx,
                    evidence_spans=evidence,
                )
                chunks.append(chunk)

        return chunks

    # ChromaDB에 생성한 KnowledgeChunk 저장
    def run_and_store(self, corpus: PaperCorpus) -> List[KnowledgeChunk]:
        """
        Execute extraction and persist resulting KnowledgeChunks into ChromaDB.

        - Includes side effects (vector DB write)
        - Intended for ingestion pipeline
        """
        chunks = self.run(corpus)

        if chunks:
            try:
                add_chunks_to_chromadb(chunks)
            except Exception as e:
                print("[Extractor Agent] Failed to store chunks:", e)

        return chunks

    # ---------- Step 1: Claim extraction ----------
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

        # LLM이 단일 claim 객체를 반환하는 구조
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

        chunk_id = f"{paper.pmid}_claim_{idx}"

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