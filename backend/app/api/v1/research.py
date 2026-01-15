# app/api/v1/research.py
import json
import os
import traceback
from pathlib import Path
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.research import ResearchRequest
from app.models.pipeline import StagedPaper
from app.models.chat import Message

from app.agents.retriever.arxiv_fetcher import ArxivFetcher
from app.core.llm import call_llm

# config.py에 get_uploads_dir()가 있으면 그걸 쓰고,
# 없으면 /app/uploads로 fallback
try:
    from app.core.config import get_uploads_dir  # type: ignore
except Exception:
    def get_uploads_dir() -> Path:
        d = Path("/app/uploads").resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d


router = APIRouter(prefix="/sessions", tags=["research"])


# ------------------------------------------------------------
# Path utils: "에이전트가 저장한 파일"을 서버가 검증하고 DB에 기록
# ------------------------------------------------------------
def _resolve_pdf_path(raw_path: Optional[str], uploads_dir: Path) -> Optional[Path]:
    """
    fetcher가 반환한 pdf_storage_path를 절대경로로 보정.
    - 절대경로면 그대로 resolve
    - 상대경로면 /app 기준이 아니라 "uploads_dir의 부모(/app)" 기준으로 보정
      (상대경로가 data/uploads/... 같은 형태여도 /app/data/uploads로 맞춰짐)
    """
    if not raw_path:
        return None

    p = Path(str(raw_path).strip())
    if p.is_absolute():
        return p.resolve()

    # 상대경로는 프로젝트 루트(/app) 기준으로 보정
    # uploads_dir = /app/uploads -> parent = /app
    base = uploads_dir.parent
    return (base / p).resolve()


def _file_exists(p: Optional[Path]) -> bool:
    try:
        return bool(p and p.exists() and p.is_file())
    except Exception:
        return False


# ------------------------------------------------------------
# Query analysis -> arXiv용 영문 키워드
# ------------------------------------------------------------
def analyze_user_input(user_text: str) -> dict:
    prompt = f"""
You are a specialized Query Analyst for arXiv.
The user may ask in Korean. Convert the user's request into effective ENGLISH search keywords for arXiv.

[User Input]
"{user_text}"

Output JSON ONLY:
{{
  "is_clear": true,
  "intent": "English search keywords...",
  "filters": {{ "max_results": 5 }}
}}
"""
    try:
        resp = call_llm(prompt, temperature=0)
        s, e = resp.find("{"), resp.rfind("}")
        if s != -1 and e != -1:
            return json.loads(resp[s : e + 1])
    except Exception as e:
        print(f"[Query Analysis Error] {e}")

    return {"is_clear": True, "intent": "Alzheimer's disease", "filters": {"max_results": 5}}


# ------------------------------------------------------------
# POST /sessions/{session_id}/research
# - is_confirmed=False: proposal
# - is_confirmed=True : fetch + download + DB save
# ------------------------------------------------------------
@router.post("/{session_id}/research")
def research(
    session_id: UUID,
    payload: ResearchRequest,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    # 사용자가 확인 전 단계면 user 메시지 저장
    if not payload.is_confirmed:
        db.add(Message(session_id=session_id, user_email=email, role="user", content=payload.query))
        db.commit()

    def event_generator():
        try:
            uploads_dir = get_uploads_dir()  # ✅ 단일 저장소 (예: /app/uploads)
            fetcher = ArxivFetcher(download_dir=str(uploads_dir))  # ✅ 에이전트가 여기에 저장

            # ----------------------------
            # CASE 1: proposal
            # ----------------------------
            if not payload.is_confirmed:
                yield json.dumps(
                    {"type": "log", "content": "🤔 arXiv 검색을 위한 키워드를 분석 중입니다..."},
                    ensure_ascii=False,
                ) + "\n"

                analysis = analyze_user_input(payload.query)
                intent = analysis.get("intent", payload.query)
                max_results = analysis.get("filters", {}).get("max_results", 5)

                msg = (
                    f"**[arXiv 검색 제안]**\n"
                    f"🎯 **영문 키워드**: `{intent}`\n"
                    f"📊 **목표 수량**: {max_results}건\n\n"
                    f"이 키워드로 arXiv에서 실물 PDF를 검색할까요?"
                )

                yield json.dumps(
                    {"type": "proposal", "content": msg, "analysis": analysis},
                    ensure_ascii=False,
                ) + "\n"
                return

            # ----------------------------
            # CASE 2: run search + download + DB save
            # ----------------------------
            confirmed = payload.confirmed_intent or {}
            search_query = confirmed.get("intent", payload.query)
            max_results = confirmed.get("filters", {}).get("max_results", 5)

            yield json.dumps(
                {"type": "log", "content": f"🚀 arXiv 검색 시작: {search_query} (최대 {max_results}건)"},
                ensure_ascii=False,
            ) + "\n"

            # ✅ 에이전트가 다운로드까지 수행하고 papers에 pdf_storage_path를 넣어줌
            papers = fetcher.search_and_download(
                search_query,
                max_results=max_results,
                query_id=str(session_id),
            )

            if not papers:
                msg = "arXiv 검색 결과가 없습니다. 다른 키워드를 시도해 보세요."
                db.add(Message(session_id=session_id, user_email=email, role="ai", content=msg))
                db.commit()
                yield json.dumps({"type": "message", "content": msg}, ensure_ascii=False) + "\n"
                return

            saved: List[StagedPaper] = []
            pdf_ok = 0

            print(f"\n[Research] === DB 적재 시작 ({len(papers)}건) ===")

            for p in papers:
                p_data = p.model_dump() if hasattr(p, "model_dump") else p.__dict__

                # ✅ 프론트가 path를 주는 구조 자체가 없음 (payload 무시/비사용)
                raw_pdf = (
                    p_data.get("pdf_storage_path")
                    or p_data.get("pdf_path")
                    or p_data.get("pdf_local_path")
                )

                resolved_pdf = _resolve_pdf_path(raw_pdf, uploads_dir)
                exists = _file_exists(resolved_pdf)

                # 존재 검증 로그 (진짜 원인 찾기 좋게)
                print(f"[Research] pdf raw={raw_pdf} resolved={resolved_pdf} exists={exists}")

                if exists:
                    pdf_ok += 1

                abstract_text = ""
                if p_data.get("abstract_sentences"):
                    abstract_text = " ".join([getattr(s, "text", "") for s in p_data["abstract_sentences"]])

                staged = StagedPaper(
                    session_id=session_id,
                    user_email=email,
                    source="arxiv",
                    title=p_data.get("title"),
                    authors=", ".join(p_data.get("authors", [])),
                    year=p_data.get("year", None),
                    url=p_data.get("url"),
                    abstract=abstract_text,
                    # ✅ 핵심: 서버가 "파일 존재" 검증한 경우에만 DB에 path 기록
                    pdf_storage_path=str(resolved_pdf) if exists else None,
                )
                db.add(staged)
                saved.append(staged)

            db.commit()

            # ✅ 업로드처럼: PDF가 확보된 StagedPaper는 백그라운드에서 자동 Extract 실행
            try:
                from app.api.v1.extract import auto_extract_staged_paper  # lazy import (순환 방지)
                for sp in saved:
                    if sp.pdf_storage_path:
                        background_tasks.add_task(
                            auto_extract_staged_paper,
                            session_id=session_id,
                            staged_paper_id=sp.id,
                            user_email=email,
                        )
            except Exception as e:
                print(f"[Research] auto_extract_staged_paper hook failed: {e}")

            print(f"[Research] DB 적재 완료. (총: {len(saved)}, PDF확보: {pdf_ok})")

            # UI용 메시지
            lines = []
            for i, sp in enumerate(saved):
                status = "✅(PDF)" if sp.pdf_storage_path else "❌(No PDF)"
                lines.append(f"{i+1}. {sp.title} {status}")

            final_msg = (
                f"✅ **arXiv 검색 및 적재 완료**\n\n"
                f"- 총 {len(saved)}건 적재\n"
                f"- 실물 PDF {pdf_ok}건 로컬 저장 확인\n\n"
                + "\n".join(lines)
            )

            db.add(Message(session_id=session_id, user_email=email, role="ai", content=final_msg))
            db.commit()

            yield json.dumps({"type": "result", "content": final_msg}, ensure_ascii=False) + "\n"

        except Exception as e:
            print(f"❌ [Research Error]\n{traceback.format_exc()}")
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson", background=background_tasks)


# ------------------------------------------------------------
# GET /sessions/{session_id}/research/candidates
# 프론트의 library 탭이 호출하는 후보 목록
# ------------------------------------------------------------
@router.get("/{session_id}/research/candidates")
def list_candidates(
    session_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    papers = (
        db.query(StagedPaper)
        .filter(StagedPaper.session_id == session_id, StagedPaper.user_email == email)
        .order_by(StagedPaper.created_at.desc())
        .all()
    )

    out = []
    for p in papers:
        has_pdf = bool(p.pdf_storage_path and os.path.exists(p.pdf_storage_path))
        out.append(
            {
                "id": str(p.id),
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "url": p.url,
                "abstract": p.abstract or "",
                "has_pdf": has_pdf,
                "source": p.source,
                "status": "staged",
            }
        )
    return out


# ------------------------------------------------------------
# ✅ 프론트가 쓰는 경로: /sessions/{id}/papers/{paper_id}/download
# - DB에서 pdf_storage_path를 찾아 FileResponse로 서빙
# ------------------------------------------------------------
@router.get("/{session_id}/papers/{paper_id}/download")
def download_paper_pdf(
    session_id: UUID,
    paper_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    paper = (
        db.query(StagedPaper)
        .filter(
            StagedPaper.id == paper_id,
            StagedPaper.session_id == session_id,
            StagedPaper.user_email == email,
        )
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.pdf_storage_path or not os.path.exists(paper.pdf_storage_path):
        raise HTTPException(status_code=404, detail="PDF file not available on server")

    safe_name = (paper.title or "paper").replace("/", "_")[:80]
    return FileResponse(
        path=paper.pdf_storage_path,
        filename=f"{safe_name}.pdf",
        media_type="application/pdf",
    )


# ------------------------------------------------------------
# ✅ alias: 예전 경로를 쓰던 코드가 있으면 깨지지 않게 유지
# /sessions/{id}/research/papers/{paper_id}/download
# ------------------------------------------------------------
@router.get("/{session_id}/research/papers/{paper_id}/download")
def download_paper_pdf_alias(
    session_id: UUID,
    paper_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    return download_paper_pdf(session_id=session_id, paper_id=paper_id, email=email, db=db)

@router.get("/{session_id}/papers/{paper_id}/summary")
def get_staged_paper_summary(
    session_id: UUID,
    paper_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    paper = (
        db.query(StagedPaper)
        .filter(
            StagedPaper.id == paper_id,
            StagedPaper.session_id == session_id,
            StagedPaper.user_email == email,
        )
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # summary 컬럼이 없거나 아직 생성 전이면 빈 문자열로 돌려도 됨
    return {"paper_id": str(paper.id), "summary": paper.summary or ""}