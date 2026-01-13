# app/agents/extractor/nodes.py
from __future__ import annotations

import uuid, json, re
from typing import Any, Dict

from app.schemas.fact import Fact, EntitySet, ExperimentInfo, RelationInfo
from app.agents.extractor.state import ExtractorState
from app.core.llm import llm_client, DEFAULT_LLM_MODEL


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


def extract_entities_with_llm(sentence: str) -> EntitySet:
    prompt = f"""
    다음 문장에서 바이오메디컬 엔티티를 추출하라.

    문장:
    "{sentence}"

    JSON 형식으로만 출력:
    {{
      "target": [],
      "disease": [],
      "organ": [],
      "compound": []
    }}
    """

    resp = llm_client.chat.completions.create(
        model=DEFAULT_LLM_MODEL,
        messages=[
            {"role": "system", "content": "너는 바이오메디컬 엔티티 추출기이다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    try:
        data = json.loads(resp.choices[0].message.content)
        return EntitySet(**data)
    except Exception:
        # fallback
        return EntitySet(target=[], disease=[], organ=[], compound=[])


def extract_entities(state: ExtractorState) -> ExtractorState:
    sent = (state["current"] or {}).get("text", "")

    if not sent:
        state["entities"] = EntitySet(target=[], disease=[], organ=[], compound=[])
        return state

    entities = extract_entities_with_llm(sent)

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


# JSON 추출 강제
def safe_json_load(text: str) -> dict | None:
    """
    LLM 응답에서 JSON 블록만 안전하게 추출
    """
    try:
        return json.loads(text)
    except Exception:
        pass

    # ```json ... ``` 제거
    cleaned = re.sub(r"```json|```", "", text).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 중괄호 블록만 추출
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return None


RELATION_SCHEMA_FALLBACK = {
    "relation": "unknown",
    "effect": "unknown",
    "evidence_strength": "unknown",
    "rationale": ""
}

def extract_relation_with_llm(sentence: str, target: str | None = None, disease: str | None = None) -> dict:
    prompt = f"""
    너는 바이오메디컬 문장에서 '타깃 치료 가능성' 관련 관계를 판정하는 정보추출기다.
    
    [입력]
    - target: {target or "미지정"}
    - disease: {disease or "미지정"}
    - sentence: "{sentence}"
    
    [판정 기준]
    1. relation은 이 문장이 target이 disease의 치료 타깃으로서 유효함을 시사하는지에 대한 해석적 판단이다.
    2. effect는 문장에 직접적으로 나타난 생물학적 변화의 유형이다.
    3. 문장에 명시적 치료 주장 없이 실험 결과만 있는 경우에도 effect는 구체적으로 판정하되 relation은 neutral로 둘 수 있다.
    
    [출력 규칙]
    1) 반드시 JSON만 출력한다.
    2) 키는 다음 4개만 사용한다: relation, effect, evidence_strength, rationale

    [값 정의]

    relation (치료적 해석):
    - support        : 타깃이 질환 치료에 유의미함을 지지
    - refute         : 타깃이 치료적으로 부적절함을 시사
    - neutral        : 실험 결과는 있으나 치료적 판단은 직접적이지 않음
    - speculative    : 가능성만 암시됨
    - unknown        : 판단 불가
    
    effect (생물학적 효과):
    - inhibition         : 억제 (예: inhibition, suppressed)
    - activation         : 활성화
    - increase           : 증가
    - decrease           : 감소
    - no_change          : 변화 없음
    - mixed              : 상반된 결과
    - association        : 연관성만 제시
    - unknown            : 명확하지 않음
    
    evidence_strength:
    - in_vitro | in_vivo | clinical | review | unknown

    [rationale]
    - 판단 근거를 한 문장으로 간단히 설명한다.
    
    """

    resp = llm_client.chat.completions.create(
        model=DEFAULT_LLM_MODEL,
        messages=[
            {"role": "system", "content": "You extract structured relation labels from biomedical sentences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )

    text = (resp.choices[0].message.content or "").strip()

    parsed = safe_json_load(text)

    if not parsed:
        return dict(RELATION_SCHEMA_FALLBACK)

    # 최소 키 보정
    for k, v in RELATION_SCHEMA_FALLBACK.items():
        parsed.setdefault(k, v)

    return parsed

def extract_relation(state: ExtractorState) -> ExtractorState:
    cur = state.get("current") or {}
    entities = state.get("entities")

    if not cur:
        state["relation"] = RelationInfo(
            stance="unknown",
            effect="unknown",
            evidence_strength="unknown",
        )
        return state

    target = entities.target[0] if entities and entities.target else None
    disease = entities.disease[0] if entities and entities.disease else None

    data = extract_relation_with_llm(
        sentence=cur["text"],
        target=target,
        disease=disease,
    )

    state["relation"] = RelationInfo(
        stance=data["relation"],
        effect=data["effect"],
        evidence_strength=data["evidence_strength"],
        rationale=data.get("rationale"),
    )
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