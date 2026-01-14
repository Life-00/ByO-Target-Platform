# app/agents/extractor/agent.py

from typing import List

from app.agents.extractor.prompts import (
    extract_claims_prompt,
    relation_inference_prompt,
)
from app.agents.extractor.parser import (
    parse_json_response,
    normalize_enum,
    normalize_optional_str,
    clamp_confidence,
)
from app.schemas.paper import PaperCorpus
from app.schemas.knowledge import KnowledgeChunk
from app.core.llm import call_llm


EFFECT_DIRECTION_ALLOWED = {
    "increase",
    "decrease",
    "modulate",
    "no_significant_effect",
    "unknown",
}

EVIDENCE_ALLOWED = {
    "in_vitro",
    "in_vivo",
    "clinical",
    "review",
    "unknown",
}


class ExtractorAgent:
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence

    def run(self, corpus: PaperCorpus) -> List[KnowledgeChunk]:
        chunks: List[KnowledgeChunk] = []

        for paper in corpus.papers:
            claims = self._extract_claims(paper.abstract)

            for item in claims:
                relation = self._infer_relation(item["claim"])

                if relation["confidence"] < self.min_confidence:
                    continue

                chunk = self._assemble_chunk(
                    paper=paper,
                    claim=item["claim"],
                    source_sentence_id=item["source_sentence_id"],
                    relation=relation,
                )
                chunks.append(chunk)

        return chunks

    # ---------- Step 1: claim extraction ----------

    def _extract_claims(self, abstract: str) -> List[dict]:
        prompt = extract_claims_prompt(abstract)
        response = call_llm(prompt)
        data = parse_json_response(response)

        return data.get("claims", [])

    # ---------- Step 2: relation inference ----------

    def _infer_relation(self, claim: str) -> dict:
        prompt = relation_inference_prompt(claim)
        response = call_llm(prompt)
        obj = parse_json_response(response)

        return {
            "stance_description": normalize_optional_str(
                obj.get("stance_description")
            ),
            "effect_direction": normalize_enum(
                obj.get("effect_direction"),
                EFFECT_DIRECTION_ALLOWED,
                "unknown",
            ),
            "effect_descriptor": normalize_optional_str(
                obj.get("effect_descriptor")
            ),
            "outcome_measure": normalize_optional_str(
                obj.get("outcome_measure")
            ),
            "evidence_level": normalize_enum(
                obj.get("evidence_level"),
                EVIDENCE_ALLOWED,
                "unknown",
            ),
            "confidence": clamp_confidence(obj.get("confidence")),
        }

    # ---------- Step 3: chunk assembly ----------

    def _assemble_chunk(
        self,
        paper,
        claim: str,
        source_sentence_id: int,
        relation: dict,
    ) -> KnowledgeChunk:
        return KnowledgeChunk(
            chunk_id=f"{paper.pmid}_{source_sentence_id}",
            chunk_type="scientific_claim",
            pmid=paper.pmid,
            query_id=paper.query_id,
            target=paper.target,
            disease=paper.disease,
            claim=claim,
            confidence=relation["confidence"],
            evidence_level=relation["evidence_level"],
            metadata={
                "stance_description": relation["stance_description"],
                "effect_direction": relation["effect_direction"],
                "effect_descriptor": relation["effect_descriptor"],
                "outcome_measure": relation["outcome_measure"],
                "paper_title": paper.title,
                "journal": paper.journal,
                "year": paper.year,
                "source_sentence_id": source_sentence_id,
            },
        )