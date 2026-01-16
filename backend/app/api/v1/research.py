# app/api/v1/research.py
import json
import traceback
from pathlib import Path
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.research import ResearchRequest
from app.models.pipeline import StagedPaper
from app.models.chat import Message
from app.core.llm import call_llm

from app.agents.retriever.europe_pmc_fetcher import EuropePMCFetcher
from app.agents.retriever.biorxiv_fetcher import BiorxivFetcher

try:
    from app.core.config import get_uploads_dir  # type: ignore
except Exception:
    def get_uploads_dir() -> Path:
        d = Path("/app/uploads").resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d

router = APIRouter(prefix="/sessions", tags=["research"])


def analyze_user_input(user_text: str) -> dict:
    """
    바이오/의료/신약개발 특화:
    - Europe PMC query language(간단 버전)로 쓸 수 있는 키워드 생성
    - 소스 우선순위: peer-reviewed + preprint(bioRxiv)
    """
    prompt = f"""
You are a biomedical literature Query Analyst.
The user may ask in Korean. Convert the user's request into effective ENGLISH search keywords for Europe PMC.
Also propose filters optimized for drug discovery / biomedical research.

[User Input]
"{user_text}"

Output JSON ONLY:
{{
  "is_clear": true,
  "intent": "English keywords",
  "filters": {{
    "max_results": 10,
    "year_from": 2019,
    "year_to": null,
    "open_access_prefer": true,
    "include_preprints": true
  }}
}}
"""
    try:
        resp = call_llm(prompt, temperature=0)
        s, e = resp.find("{"), resp.rfind("}")
        if s != -1 and e != -1:
            return json.loads(resp[s:e+1])
    except Exception as e:
        print(f"[Query Analysis Error] {e}")

    return {
        "is_clear": True,
        "intent": user_text,
        "filters": {"max_results": 10, "year_from": None, "year_to": None, "open_access_prefer": True, "include_preprints": True},
    }


import re

# 너무 일반적인 단어(검색에 넣으면 잡음만 늘거나 0건을 만들기 쉬운 토큰)
GENERIC_STOP = {
    "symptoms", "treatment", "prevention", "epidemiology", "pathophysiology",
    "immune response", "clinical trials", "drug discovery", "therapeutic targets",
    "review", "mechanism", "pathway", "therapy"
}

# 의미없는 응답/토큰
BAD_TOKENS = {"", "n/a", "na", "none", "null", "unknown", "general", "etc"}

def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _split_terms(text: str) -> list[str]:
    text = _normalize_spaces(text)
    if not text:
        return []

    # comma/semicolon/slash 기준 분해
    raw = re.split(r"[;,/]+", text)
    out = []
    for t in raw:
        t = _normalize_spaces(t)
        if not t:
            continue
        out.append(t)
    return out

def _is_valid_term(t: str) -> bool:
    tl = t.lower().strip()
    if tl in BAD_TOKENS:
        return False
    # 너무 짧은 토큰 제거
    if len(tl) < 3:
        return False
    # 숫자/기호만 있는 토큰 제거
    if re.fullmatch(r"[\W_]+", tl):
        return False
    return True

def _filter_generic(terms: list[str]) -> list[str]:
    out = []
    for t in terms:
        tl = t.lower().strip()
        if tl in GENERIC_STOP:
            continue
        out.append(t)
    return out

def _rank_terms(terms: list[str]) -> list[str]:
    """
    간단 휴리스틱:
    - 공백 포함(=구문) 우선 ("common cold" 같이)
    - 너무 긴 구문은 제외(>60 chars)
    - 중복 제거(소문자 기준)
    """
    seen = set()
    cleaned = []
    for t in terms:
        tl = t.lower()
        if tl in seen:
            continue
        seen.add(tl)
        if len(t) > 60:
            continue
        cleaned.append(t)

    def score(t: str) -> tuple[int, int]:
        # phrase(공백)면 +1, 길이가 적당하면 +1
        is_phrase = 1 if " " in t else 0
        length_bonus = 1 if 4 <= len(t) <= 30 else 0
        return (is_phrase, length_bonus)

    return sorted(cleaned, key=score, reverse=True)

def build_epmc_query(
    intent: str,
    year_from: int | None,
    year_to: int | None,
    include_preprints: bool,
    fallback_text: str | None = None,   # ✅ 추가: 사용자 원문 백업
) -> str:
    """
    - intent가 엉망이어도 cancer로 튀지 않게
    - 유효 키워드를 최대한 추출해서 Europe PMC 쿼리로 변환
    """

    # 1) intent에서 후보 추출
    terms = _split_terms(intent)
    terms = [t for t in terms if _is_valid_term(t)]
    terms = _filter_generic(terms)
    terms = _rank_terms(terms)

    # 2) intent가 부실하면 fallback_text에서 다시 후보 추출
    if not terms and fallback_text:
        ft = _split_terms(fallback_text)
        ft = [t for t in ft if _is_valid_term(t)]
        ft = _rank_terms(ft)
        terms = ft

    # 3) 그래도 없으면 "cancer" 같은 무의미 기본값 대신 user 원문(최후의 수단)
    if not terms:
        # 여기서도 고정 키워드(cancer) 대신 안전하게 원문을 쓰는 편이 낫다
        # 다만 완전 공백이면 마지막으로 broad term 사용
        safe = _normalize_spaces(fallback_text or "") or "infection"
        terms = [safe]

    # 4) 최종은 2~4개 정도가 적절 (너무 적으면 recall↓, 너무 많으면 0건↑)
    terms = terms[:4]

    # 5) OR 블록 생성
    or_block = " OR ".join([f"\"{t}\"" if " " in t else t for t in terms])
    q = f"({or_block})"

    # 6) 연도 필터
    if year_from or year_to:
        y0 = year_from or 1900
        y1 = year_to or 3000
        q += f" AND PUB_YEAR:[{y0} TO {y1}]"

    return q


def _resolve_pdf_path(raw_path: Optional[str], uploads_dir: Path) -> Optional[Path]:
    if not raw_path:
        return None
    p = Path(str(raw_path).strip())
    if p.is_absolute():
        return p.resolve()
    base = uploads_dir.parent
    return (base / p).resolve()


def _file_exists(p: Optional[Path]) -> bool:
    try:
        return bool(p and p.exists() and p.is_file())
    except Exception:
        return False


@router.post("/{session_id}/research")
def research(
    session_id: UUID,
    payload: ResearchRequest,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    if not payload.is_confirmed:
        db.add(Message(session_id=session_id, user_email=email, role="user", content=payload.query))
        db.commit()

    def event_generator():
        try:
            uploads_dir = get_uploads_dir()
            epmc = EuropePMCFetcher()
            biorxiv = BiorxivFetcher(download_dir=str(uploads_dir))

            # ----------------------------
            # CASE 1: proposal
            # ----------------------------
            if not payload.is_confirmed:
                yield json.dumps({"type": "log", "content": "🤔 Europe PMC(+bioRxiv) 검색 전략을 분석 중입니다."}, ensure_ascii=False) + "\n"

                analysis = analyze_user_input(payload.query)
                intent = analysis.get("intent", payload.query)
                f = analysis.get("filters", {}) or {}
                msg = (
                    f"**[바이오 문헌 검색 제안]**\n"
                    f"🎯 **키워드**: `{intent}`\n"
                    f"📊 **목표 수량**: {f.get('max_results', 10)}건\n"
                    f"🗓️ **연도 필터**: {f.get('year_from')} ~ {f.get('year_to')}\n"
                    f"🧾 **Preprint 포함**: {bool(f.get('include_preprints', True))}\n\n"
                    f"이 설정으로 Europe PMC에서 검색하고, 가능하면 PDF까지 확보할까요?"
                )
                yield json.dumps({"type": "proposal", "content": msg, "analysis": analysis}, ensure_ascii=False) + "\n"
                return

            # ----------------------------
            # CASE 2: execution
            # ----------------------------
            confirmed = payload.confirmed_intent or {}
            intent = confirmed.get("intent", payload.query)
            f = confirmed.get("filters", {}) or {}

            max_results = int(f.get("max_results", 10))
            year_from = f.get("year_from")
            year_to = f.get("year_to")
            include_preprints = bool(f.get("include_preprints", True))

            epmc_query = build_epmc_query(intent=intent, year_from=year_from, year_to=year_to, include_preprints=include_preprints)

            yield json.dumps({"type": "log", "content": f"🚀 Europe PMC 검색 시작: {epmc_query} (최대 {max_results}건)"}, ensure_ascii=False) + "\n"

            results = epmc.search(query=epmc_query, page_size=max_results, sort="relevance")
            if not results:
                msg = "Europe PMC 검색 결과가 없습니다. 다른 키워드/필터로 시도해 보세요."
                db.add(Message(session_id=session_id, user_email=email, role="ai", content=msg))
                db.commit()
                yield json.dumps({"type": "message", "content": msg}, ensure_ascii=False) + "\n"
                return

            # Paper 변환 + PDF 다운로드 시도
            staged_rows: List[StagedPaper] = []
            for r in results:
                paper = epmc.to_paper(r, query_id=str(session_id), retrieval_reason="europe_pmc_search")

                pdf_path = None
                # bioRxiv인 경우 DOI로 PDF 다운로드 시도
                if (paper.source or "").lower() == "biorxiv" and getattr(r, "doi", None):
                    pdf_path = biorxiv.download_pdf(doi=r.doi, file_stem=f"biorxiv_{r.id}")

                resolved = _resolve_pdf_path(pdf_path, uploads_dir) if pdf_path else None
                pdf_storage_path = str(resolved) if _file_exists(resolved) else None

                # StagedPaper 저장(모델 필드명은 프로젝트 기준으로 맞춰야 함)
                sp = StagedPaper(
                    session_id=session_id,
                    user_email=email,
                    title=paper.title,
                    abstract=" ".join([s.text for s in paper.abstract_sentences]) if paper.abstract_sentences else "",
                    year=paper.year,
                    source=paper.source or "europe_pmc",
                    url=paper.url,
                    pdf_storage_path=pdf_storage_path,
                )
                db.add(sp)
                staged_rows.append(sp)

            db.commit()

            yield json.dumps({"type": "log", "content": f"✅ 저장 완료: {len(staged_rows)}건 (StagedPaper)"}, ensure_ascii=False) + "\n"

            # 사용자에게 요약 메시지 저장
            msg = f"✅ Europe PMC 검색 결과 {len(staged_rows)}건을 저장했습니다. 이제 문서를 선택한 뒤 Extract를 실행할 수 있습니다."
            db.add(Message(session_id=session_id, user_email=email, role="ai", content=msg))
            db.commit()

            yield json.dumps({"type": "result", "data": {"count": len(staged_rows)}}, ensure_ascii=False) + "\n"

        except Exception as e:
            print("[Research Error]", e)
            traceback.print_exc()
            yield json.dumps({"type": "error", "content": f"오류 발생: {str(e)}"}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
