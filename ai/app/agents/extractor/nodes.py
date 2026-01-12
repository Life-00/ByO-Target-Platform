# app/agents/extractor/nodes.py
from __future__ import annotations

import uuid
from typing import Any, Dict

from app.schemas.fact import Fact, EntitySet, ExperimentInfo, RelationInfo
from app.agents.extractor.state import ExtractorState


def iterate_sentences(state: ExtractorState) -> ExtractorState:
    if "sentence_queue" not in state:
        queue = []
        for p in state["papers"]:
            for s in p.abstract_sentences:
                queue.append((p.pmid, s.sentence_id, s.text))
        state["sentence_queue"] = queue

    if not state["sentence_queue"]:
        state["current"] = None
        return state

    pmid, sid, text = state["sentence_queue"].pop(0)
    state["current"] = {"pmid": pmid, "sentence_id": sid, "text": text}
    return state


def extract_entities(state: ExtractorState) -> ExtractorState:
    sent = (state["current"] or {}).get("text", "")
    entities = EntitySet(target=[], disease=[], organ=[], compound=[])

    # MVP rule examples
    # (실제는 LLM/function calling으로 교체)
    for token in ["EGFR", "TNF", "TP53", "IL6"]:
        if token in sent:
            entities.target.append(token)

    state["entities"] = entities
    return state


def extract_experiment(state: ExtractorState) -> ExtractorState:
    sent = (state["current"] or {}).get("text", "").lower()

    model = "unknown"
    species = "unknown"

    if "mouse" in sent or "mice" in sent:
        model, species = "animal", "mouse"
    elif "rat" in sent:
        model, species = "animal", "rat"
    elif "patient" in sent or "clinical" in sent or "trial" in sent:
        model, species = "human", "human"
    elif "cell" in sent or "in vitro" in sent:
        model, species = "cell", "unknown"

    state["experiment"] = ExperimentInfo(model=model, species=species, assay=None)
    return state


def extract_relation(state: ExtractorState) -> ExtractorState:
    sent = (state["current"] or {}).get("text", "").lower()

    rtype = "unknown"
    if any(k in sent for k in ["increased", "upregulated", "elevated"]):
        rtype = "increase"
    elif any(k in sent for k in ["decreased", "downregulated", "reduced"]):
        rtype = "decrease"
    elif any(k in sent for k in ["no effect", "not significant"]):
        rtype = "no_effect"
    elif any(k in sent for k in ["associated with", "correlated with"]):
        rtype = "association"

    state["relation"] = RelationInfo(type=rtype, object=None)
    return state


def assemble_fact(state: ExtractorState) -> ExtractorState:
    cur = state.get("current")
    if not cur:
        return state

    fact = Fact(
        fact_id=str(uuid.uuid4()),
        pmid=cur["pmid"],
        sentence_id=cur["sentence_id"],
        text=cur["text"],
        entities=state["entities"],
        experiment=state["experiment"],
        relation=state["relation"],
    )

    if "extracted_facts" not in state:
        state["extracted_facts"] = []
    state["extracted_facts"].append(fact)
    return state