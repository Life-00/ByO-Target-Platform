# app/agents/extractor/agent.py

from __future__ import annotations
from typing import List

from app.agents.extractor.prompts import claim_extraction_prompt
from app.agents.extractor.parser import (
    parse_json_response,
    ExtractedClaim,
)
from app.schemas.retrieval import PaperCorpus, Paper
from app.schemas.knowledge import KnowledgeChunk
from app.core.llm import call_llm

from app.services.chromadb.ingest_chunk import add_chunks_to_chromadb

print(">>> USING UPDATED ExtractorAgent (LLM-only, no enums) <<<")

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

                chunk = self._assemble_chunk(
                    paper=paper,
                    extracted=claim,
                    idx=idx,
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
                print("[ExtractorAgent] Failed to store chunks:", e)

        return chunks


    # ---------- Step 1: Claim extraction ----------
    def _extract_claims(self, paper: Paper) -> List[ExtractedClaim]:
        """
        LLM returns a SINGLE structured claim object.
        We wrap it into a list for uniform downstream handling.
        """

        sentence_payload = [
            {"sentence_id": s.sentence_id, "text": s.text}
            for s in (paper.abstract_sentences or [])
            if s.text
        ]

        if not sentence_payload:
            return []

        prompt = claim_extraction_prompt(sentence_payload)
        response = call_llm(prompt)

        # 디버깅
        # print("\n[DEBUG extract_claims LLM raw response]\n", response)

        # LLM이 단일 claim 객체를 반환하는 구조
        try:
            data = parse_json_response(response)
            extracted = ExtractedClaim(**data)
            return [extracted]
        except Exception as e:
            print("[Extractor] Failed to parse ExtractedClaim:", e)
            return []

        # data = parse_json_response(response)
        # raw_claims = data.get("claims", [])
        #
        # try:
        #     extracted_claim = ExtractedClaim(**data)
        #     return [extracted_claim]
        # except Exception as e:
        #     print("[Extractor] Failed to parse ExtractedClaim:", e)
        #     return []

    # ---------- Step 2: KnowledgeChunk assembly ----------

    def _assemble_chunk(
        self,
        paper: Paper,
        extracted: ExtractedClaim,
        idx: int,
    ) -> KnowledgeChunk:
        """
        Assemble KnowledgeChunk directly from LLM-extracted claim.
        """

        # Stable, traceable chunk id
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
            # "source_sentence_id": extracted.source_sentence_id,
            "notes": extracted.notes
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

            chunk_type="claim",  # neutral default; refine later
            metadata=metadata,
        )
