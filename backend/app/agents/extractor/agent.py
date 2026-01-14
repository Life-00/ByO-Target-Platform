# app/agents/extractor/agent.py

from __future__ import annotations
from typing import List, Optional

from app.agents.extractor.prompts import claim_extraction_prompt
from app.agents.extractor.parser import parse_json_response, ExtractedClaim
from app.schemas.retrieval import PaperCorpus, Paper
from app.schemas.knowledge import KnowledgeChunk
from app.core.llm import call_llm

class ExtractorAgent:
    def __init__(self, min_confidence: float = 0.0):
        self.min_confidence = min_confidence

    # ✅ instruction 파라미터 추가
    def run(self, corpus: PaperCorpus, instruction: Optional[str] = None) -> List[KnowledgeChunk]:
        chunks: List[KnowledgeChunk] = []

        for paper in corpus.papers:
            # instruction 전달
            extracted_claims = self._extract_claims(paper, instruction)

            for idx, claim in enumerate(extracted_claims):
                if claim.confidence is not None and claim.confidence < self.min_confidence:
                    continue

                chunk = self._assemble_chunk(paper=paper, extracted=claim, idx=idx)
                chunks.append(chunk)

        return chunks

    def _extract_claims(self, paper: Paper, instruction: str = None) -> List[ExtractedClaim]:
        sentence_payload = [
            {"sentence_id": s.sentence_id, "text": s.text}
            for s in (paper.abstract_sentences or [])
            if s.text
        ]

        if not sentence_payload:
            return []

        # ✅ 프롬프트에 instruction 전달
        prompt = claim_extraction_prompt(sentence_payload, instruction)
        response = call_llm(prompt)

        try:
            data = parse_json_response(response)
            extracted = ExtractedClaim(**data)
            return [extracted]
        except Exception as e:
            print("[Extractor] Failed to parse ExtractedClaim:", e)
            return []

    # ... (_assemble_chunk는 기존 유지)
    def _assemble_chunk(self, paper: Paper, extracted: ExtractedClaim, idx: int) -> KnowledgeChunk:
        chunk_id = f"{paper.pmid}_claim_{idx}"
        metadata = {
            "paper_title": paper.title,
            "journal": paper.journal,
            "year": paper.year,
            "retrieval_reason": paper.retrieval_reason,
            "salience": (extracted.salience.model_dump() if extracted.salience else None),
            "notes": extracted.notes
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