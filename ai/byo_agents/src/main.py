from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# -------------------------------------------------------------------
# ✅ 실행 위치에 상관없이 src 내부 모듈을 안정적으로 import 하기 위한 처리
# - python src/main.py 로 실행해도 동작하게 만듦
# -------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
SRC_DIR = THIS_FILE.parent
PROJECT_ROOT = SRC_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 이제 src 폴더 안의 retriever.py / synthesizer.py 를 import 가능
from retriever import PubMedClient, RetrieverAgent
from synthesizer import SynthesizerAgent


# -------------------------------------------------------------------
# ✅ 회의록 반영: 논문 수집은 "backend api"가 정석
# - 다만 아직 backend endpoint가 확정/연동 전일 수 있으니
#   BACKEND_API_URL 이 있으면 API로, 없으면 로컬(PubMedClient)로 fallback
# -------------------------------------------------------------------
def retrieve_papers(
    *,
    target: str,
    disease: str,
    topic: str,
    retmax: int = 15,
    email: str = "333434@naver.com",
) -> dict[str, Any]:
    """
    1) BACKEND_API_URL 환경변수가 있으면: backend API로 논문 수집 요청
    2) 없으면: 로컬 RetrieverAgent(PubMedClient)로 수집 (임시 fallback)
    """
    backend_url = os.getenv("BACKEND_API_URL", "").strip()

    # ✅ 1) backend api 우선(정석)
    if backend_url:
        try:
            try:
                import requests  # 외부 라이브러리 (requirements.txt에 requests 필요)
            except Exception as e:
                raise RuntimeError(
                    "BACKEND_API_URL을 설정했지만 'requests'가 설치되지 않았습니다. "
                    "pip install requests 또는 requirements.txt 설치가 필요합니다."
                ) from e

            endpoint = backend_url.rstrip("/") + "/papers/search"
            payload = {"target": target, "disease": disease, "topic": topic, "retmax": retmax}

            resp = requests.post(endpoint, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # 최소 안전장치
            papers = data.get("papers")
            if not isinstance(papers, list):
                raise ValueError("Backend response must include list field: 'papers'")

            # query가 없으면 기본 query 구성
            data.setdefault("query", f"{target} {disease} {topic}")
            return data

        except Exception as e:
            print(f"[WARN] backend retrieve failed -> fallback to local retriever. reason={e}")

    # ✅ 2) 로컬 fallback (임시)
    pubmed = PubMedClient(email=email)
    retriever = RetrieverAgent(pubmed)
    return retriever.run(target=target, disease=disease, topic=topic, retmax=retmax)


# -------------------------------------------------------------------
# ✅ Validator Agent가 아직 없을 때: Synthesizer 테스트용 스텁 JSON
# -------------------------------------------------------------------
def make_stub_validator_output(
    *,
    target: str,
    disease: str,
    papers: list[dict[str, Any]],
) -> dict[str, Any]:
    key_claims: list[dict[str, Any]] = []

    for p in papers[:3]:
        abstract = (p.get("abstract") or "").strip()

        if abstract:
            first = abstract.split(".")[0].strip()
            sentence = (first + ".") if first else "(초록 첫 문장 추출 실패)"
        else:
            sentence = "(초록 없음)"

        key_claims.append(
            {
                "claim": f"{target} 관련 주요 연구 관찰(임시 요약)",
                "evidence_level": ["Unknown"],
                "evidences": [
                    {
                        "pmid": p.get("pmid", "") or "",
                        "sentence": sentence,
                        "url": p.get("url", "") or "",
                    }
                ],
            }
        )

    return {
        "target_profile": {
            "target": target,
            "disease": disease,
            "scope_note": f"PubMed 초록 기반 {len(papers)}편 수집",
        },
        "key_claims": key_claims,
        "evidence_level_summary": {"In vitro": 0, "In vivo": 0, "Clinical": 0},
        "risk_signals": [],
        "next_validation_steps": [
            "Validator Agent 구현 후 근거 수준 분류(In vitro/In vivo/Clinical) 자동화",
            "상충 결과/리스크 신호 탐지 로직 추가",
        ],
        "options": [
            {"path": "Go (추가 검증 진행)", "rationale": "현재는 임시 요약 단계이며 Validator 구현이 필요"},
            {"path": "Hold (조건부 보류)", "rationale": "근거 수준 분류/리스크 신호 분석 전이므로 판단 유보"},
        ],
    }


# -------------------------------------------------------------------
# ✅ main
# -------------------------------------------------------------------
def main() -> None:
    target = os.getenv("TARGET", "TP53")
    disease = os.getenv("DISEASE", "hepatocellular carcinoma")
    topic = os.getenv("TOPIC", "prognosis")
    retmax = int(os.getenv("RETMAX", "15"))

    email = os.getenv("PUBMED_EMAIL", "333434@naver.com")

    # 1) Retriever 단계
    retrieved = retrieve_papers(target=target, disease=disease, topic=topic, retmax=retmax, email=email)

    papers = retrieved.get("papers", [])
    query = retrieved.get("query", f"{target} {disease} {topic}")

    print(f"[Retriever] query = {query}")
    print(f"[Retriever] papers = {len(papers)}")

    if retrieved.get("followup_request"):
        print(
            "[Retriever] followup_request:",
            json.dumps(retrieved["followup_request"], ensure_ascii=False, indent=2),
        )

    # 2) (임시) Validator 스텁
    validated_stub = make_stub_validator_output(target=target, disease=disease, papers=papers)

    # 3) Synthesizer 단계
    synth = SynthesizerAgent()
    result = synth.run(validated_stub)

    # 4) outputs/dossier.md 저장 (✅ 최소 수정: dossier_markdown 우선 사용)
    outputs_dir = PROJECT_ROOT / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    out_path = outputs_dir / "dossier.md"

    dossier_text = result.get("dossier_markdown")
    if not isinstance(dossier_text, str) or not dossier_text.strip():
        # 혹시라도 dossier_markdown이 없으면(예외 상황) 안전하게 처리
        dossier_obj = result.get("dossier", {})
        dossier_text = json.dumps(dossier_obj, ensure_ascii=False, indent=2)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(dossier_text)

    print(f"[Synthesizer] wrote {out_path}")


if __name__ == "__main__":
    main()
