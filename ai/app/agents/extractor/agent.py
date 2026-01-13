# app/agents/extractor/agent.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from uuid import uuid4

from app.schemas.retrieval import Paper
from app.schemas.query import UserQuery
from app.schemas.knowledge import KnowledgeChunk, KnowledgeDocument

from app.agents.extractor.prompts import claim_detection_prompt, entity_extraction_prompt, relation_inference_prompt,
from app.agents.extractor.parsers import parse_json_response, normalize_optional_str, normalize_enum, clamp_confidence,

from app.core.llm import llm_client
from app.services.chromadb.ingest_chunks import add_chunks_to_chromadb


STANCE_ALLOWED = {"support", "refute", "neutral", "unknown"}
EFFECT_ALLOWED = {"increase", "decrease", "no_change", "mixed", "unknown"}
EVIDENCE_ALLOWED = {"in_vitro", "in_vivo", "clinical", "review", "unknown"}


@dataclass
class ExtractorConfig:
    min_confidence: float = 0.40
    max_sentences: Optional[int] = None
    llm_retries: int = 2


class ExtractorAgent:
    """
    LLM-only Extractor Agent
    - 단계 분리
    - JSON 강제
    - 코드 조립
    """

    def __init__(self, config: Optional[ExtractorConfig] = None):
        self.config = config or ExtractorConfig()
        self.llm = get_llm_client()

    # ======================
    # Public Entrypoint
    # ======================

    def run(self, paper: Paper, query: UserQuery) -> KnowledgeDocument:
        chunks: List[KnowledgeChunk] = []

        sentences = paper.abstract_sentences or []
        if self.config.max_sentences:
            sentences = sentences[: self.config.max_sentences]

        for sent in sentences:
            claim = self._step1_detect_claim(sent.text)
            if claim is None:
                continue

            target, disease = self._step2_extract_entities(claim, query)
            if not target or not disease:
                continue

            relation = self._step3_infer_relation(claim)

            chunk = self._step4_assemble_chunk(
                paper=paper,
                query=query,
                claim=claim,
                target=target,
                disease=disease,
                relation=relation,
                source_sentence_id=sent.sentence_id,
            )

            if not self._validate_chunk(chunk):
                continue

            chunks.append(chunk)

        # Extractor는 저장을 "직접" 하지 않고 ingest layer에 위임
        if chunks:
            add_chunks_to_chromadb(chunks)

        return KnowledgeDocument(
            pmid=paper.pmid,
            query_id=query.query_id,
            extractor_version="v1-llm-only",
            chunks=chunks,
        )

    # ======================
    # Step 1. Claim Detection
    # ======================

    def _step1_detect_claim(self, sentence: str) -> Optional[str]:
        prompt = claim_detection_prompt(sentence)

        for _ in range(self.config.llm_retries + 1):
            resp = self.llm(prompt).strip()
            if resp.upper() == "NO":
                return None
            if len(resp) < 10:
                return None
            return resp

        return None

    # ======================
    # Step 2. Entity Extraction
    # ======================

    def _step2_extract_entities(
        self, claim: str, query: UserQuery
    ) -> tuple[Optional[str], Optional[str]]:
        prompt = entity_extraction_prompt(
            claim=claim,
            disease_hint=query.disease,
            target_hint=query.target_hint,
        )

        for _ in range(self.config.llm_retries + 1):
            raw = self.llm(prompt).strip()
            try:
                obj = parse_json_response(raw)
            except Exception:
                continue

            target = normalize_optional_str(obj.get("target"))
            disease = normalize_optional_str(obj.get("disease"))
            return target, disease

        return None, None

    # ======================
    # Step 3. Relation Inference
    # ======================

    def _step3_infer_relation(self, claim: str) -> dict:
        prompt = relation_inference_prompt(claim)

        for _ in range(self.config.llm_retries + 1):
            raw = self.llm(prompt).strip()
            try:
                obj = parse_json_response(raw)
            except Exception:
                continue

            return {
                "stance": normalize_enum(obj.get("stance"), STANCE_ALLOWED, "unknown"),
                "effect": normalize_enum(obj.get("effect"), EFFECT_ALLOWED, "unknown"),
                "evidence_level": normalize_enum(
                    obj.get("evidence_level"), EVIDENCE_ALLOWED, "unknown"
                ),
                "confidence": clamp_confidence(obj.get("confidence"), 0.5),
            }

        return {
            "stance": "unknown",
            "effect": "unknown",
            "evidence_level": "unknown",
            "confidence": 0.4,
        }

    # ======================
    # Step 4. Chunk Assembly
    # ======================

    def _step4_assemble_chunk(
        self,
        paper: Paper,
        query: UserQuery,
        claim: str,
        target: str,
        disease: str,
        relation: dict,
        source_sentence_id: Optional[str],
    ) -> KnowledgeChunk:
        return KnowledgeChunk(
            chunk_id=str(uuid4()),
            chunk_type="disease_target",
            pmid=paper.pmid,
            query_id=query.query_id,
            target=target,
            disease=disease,
            claim=claim,
            stance=relation["stance"],
            effect=relation["effect"],
            evidence_level=relation["evidence_level"],
            confidence=relation["confidence"],
            metadata={
                "paper_title": paper.title,
                "journal": paper.journal,
                "year": paper.year,
                "source_sentence_id": source_sentence_id,
            },
        )

    # ======================
    # Validation
    # ======================

    def _validate_chunk(self, chunk: KnowledgeChunk) -> bool:
        if not chunk.target or not chunk.disease:
            return False
        if not chunk.claim or len(chunk.claim.strip()) < 10:
            return False
        if chunk.confidence < self.config.min_confidence:
            return False
        return True
