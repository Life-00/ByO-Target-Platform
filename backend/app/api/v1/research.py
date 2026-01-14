import json
import uuid
import time
import os
from uuid import UUID
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.research import ResearchRequest
from app.models.pipeline import StagedPaper
from app.models.chat import Message

# Agent & Schema
from app.agents.retriever.agent import RetrieverAgent
from app.agents.retriever.pdf_fetcher import PDFFetcher
from app.schemas.query import UserQuery, SearchConstraints
from app.core.llm import call_llm

router = APIRouter(prefix="/sessions", tags=["research"])

# Retriever Agent 초기화
retriever_agent = RetrieverAgent(
    use_llm_expand=True,
    use_llm_filter=True,
    default_retmax=50,
    semantic_top_n=50,
    llm_keep_eval_n=10 
)

# ✅ [핵심] 초록과 요약을 구분하기 위한 특수 마커 정의
SUMMARY_MARKER = "\n\n---SUMMARY_SECTION---\n"

# ----------------------------------------------------------------
# Helper: 초록 기반 요약 생성 (PDF 없을 때 사용)
# ----------------------------------------------------------------
def generate_abstract_summary(title: str, abstract: str) -> str:
    if not abstract or len(abstract) < 50:
        return ""

    prompt = f"""
    You are a professional research assistant.
    Summarize the following academic paper based on its abstract.
    Write the report in **Korean (한국어)**.

    [Paper Info]
    Title: {title}
    Abstract: {abstract}

    [Format]
    1. **연구 목적**: 한 문장 요약.
    2. **주요 결과**: 핵심 발견 사항.
    3. **결론**: 시사점.

    Keep it concise and structured. Markdown supported.
    """
    try:
        return call_llm(prompt, temperature=0.3)
    except Exception as e:
        print(f"[Summary Error] {e}")
        return ""


# ----------------------------------------------------------------
# 사용자 자연어 분석 함수
# ----------------------------------------------------------------
def analyze_user_input(user_text: str, history: List[dict] = None) -> dict:
    history_text = ""
    if history:
        for msg in history[-5:]:
            role = "User" if msg['role'] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"
    
    prompt = f"""
    You are a specialized Query Analyst.
    
    [Conversation History]
    {history_text or "No previous conversation."}
    
    [Latest User Input]
    "{user_text}"
    
    Task:
    1. Analyze the input in context.
    2. Extract intent, target, disease.
    3. Extract filters: year_from, study_types, max_results.
    4. Do NOT invent a year filter unless explicitly stated.
    
    Output JSON ONLY:
    {{
        "is_clear": true,
        "intent": "Search keywords...",
        "target": "...",
        "disease": "...",
        "filters": {{
            "year_from": null,  
            "study_types": [],
            "max_results": 5
        }}
    }}
    """
    try:
        response = call_llm(prompt, temperature=0)
        s = response.find("{")
        e = response.rfind("}")
        if s != -1 and e != -1:
            return json.loads(response[s : e + 1])
        return {"is_clear": True, "intent": user_text, "filters": {}}
    except Exception as e:
        print(f"[Query Analysis Error] {e}")
        return {"is_clear": True, "intent": user_text, "filters": {}}

# ----------------------------------------------------------------
# Research 엔드포인트
# ----------------------------------------------------------------
@router.post("/{session_id}/research")
def research(
    session_id: UUID, 
    payload: ResearchRequest, 
    email: str = Depends(get_current_user_email), 
    db: Session = Depends(get_db)
):
    if not payload.is_confirmed:
        user_msg = Message(session_id=session_id, user_email=email, role="user", content=payload.query)
        db.add(user_msg)
        db.commit()

    def event_generator():
        try:
            pdf_fetcher = PDFFetcher(download_dir="data/uploads")
            
            # CASE 1: 분석 및 제안
            if not payload.is_confirmed:
                yield json.dumps({"type": "log", "content": "🤔 조건을 재확인하고 있습니다..."}, ensure_ascii=False) + "\n"
                
                recent_messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.desc()).limit(5).all()
                history = [{"role": m.role, "content": m.content} for m in reversed(recent_messages)]
                
                analysis = analyze_user_input(payload.query, history)
                
                if not analysis.get("is_clear", True):
                    question = "검색 주제가 명확하지 않습니다. 타겟 질환이나 유전자를 구체적으로 알려주시겠어요?"
                    db.add(Message(session_id=session_id, user_email=email, role="ai", content=question))
                    db.commit()
                    yield json.dumps({"type": "message", "content": question}, ensure_ascii=False) + "\n"
                    return

                filters = analysis.get("filters", {})
                filter_desc = []
                if filters.get("year_from"): filter_desc.append(f"{filters['year_from']}년 이후")
                if filters.get("max_results"): filter_desc.append(f"{filters['max_results']}건")
                
                filter_str = f" (조건: {', '.join(filter_desc)})" if filter_desc else ""
                
                proposal_msg = (
                    f"**[검색 전략 제안]**\n"
                    f"🎯 **주제**: {analysis.get('intent')}\n"
                    f"🧬 **타겟/질환**: {analysis.get('target') or '-'} / {analysis.get('disease') or '-'}\n"
                    f"{filter_str}\n\n"
                    f"이 조건으로 검색을 시작할까요?"
                )
                
                yield json.dumps({
                    "type": "proposal",
                    "content": proposal_msg,
                    "analysis": analysis 
                }, ensure_ascii=False) + "\n"
                return

            # CASE 2: 실제 검색
            confirmed_data = payload.confirmed_intent or {}
            final_intent = confirmed_data.get("intent", payload.query)
            raw_filters = confirmed_data.get("filters", {})
            
            target_top_k = raw_filters.get("max_results", 5)
            if not isinstance(target_top_k, int) or target_top_k < 1: target_top_k = 5

            search_intent = final_intent

            valid_types = {"in_vitro", "in_vivo", "clinical", "review", "unknown"}
            mapped_types = []
            if "study_types" in raw_filters and raw_filters["study_types"]:
                for t in raw_filters["study_types"]:
                    t_lower = t.lower()
                    if t_lower in ["clinical_trial", "clinical trial"]: mapped_types.append("clinical")
                    elif t_lower in ["meta_analysis", "meta analysis"]: mapped_types.append("review")
                    elif t_lower in valid_types: mapped_types.append(t_lower)
            
            constraints_obj = SearchConstraints(
                year_from=raw_filters.get("year_from"),
                year_to=raw_filters.get("year_to"),
                study_types=mapped_types if mapped_types else None,
                max_results=target_top_k
            )

            yield json.dumps({"type": "log", "content": f"🚀 검색 수행: {search_intent} (목표: {target_top_k}건)"}, ensure_ascii=False) + "\n"

            user_query = UserQuery(
                query_id=str(uuid.uuid4()),
                intent=search_intent,
                target_hint=confirmed_data.get("target"), 
                disease=confirmed_data.get("disease"),
                organ=confirmed_data.get("organ"),
                constraints=constraints_obj
            )

            final_corpus = None
            for step_data in retriever_agent.run_stream(user_query):
                if step_data["type"] == "log":
                    yield json.dumps(step_data, ensure_ascii=False) + "\n"
                elif step_data["type"] == "result":
                    final_corpus = step_data["data"]

            if final_corpus and final_corpus.papers:
                candidate_pool = final_corpus.papers[: max(target_top_k * 3, 10)]
                
                yield json.dumps({"type": "log", "content": f"📥 {len(candidate_pool)}개 후보 논문에 대해 PDF 다운로드 시도..."}, ensure_ascii=False) + "\n"
                
                pdf_map: Dict[str, Optional[str]] = {}
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_pmid = {executor.submit(pdf_fetcher.download_pdf, p.pmid): p.pmid for p in candidate_pool}
                    for future in as_completed(future_to_pmid):
                        pmid = future_to_pmid[future]
                        try:
                            pdf_map[pmid] = future.result()
                        except Exception:
                            pdf_map[pmid] = None

                downloaded_papers = [p for p in candidate_pool if pdf_map.get(p.pmid)]
                no_pdf_papers = [p for p in candidate_pool if not pdf_map.get(p.pmid)]
                
                final_selection = (downloaded_papers + no_pdf_papers)[:target_top_k]
                
                saved_models = []
                success_count = 0

                for p in final_selection:
                    pdf_path = pdf_map.get(p.pmid)
                    if pdf_path: success_count += 1
                    
                    abstract_text = " ".join([s.text for s in p.abstract_sentences]) if p.abstract_sentences else ""
                    
                    # ✅ [수정] PDF가 없어서 요약 생성 시, 구분자(SUMMARY_MARKER)를 사용해 병합 저장
                    final_abstract = abstract_text
                    
                    if not pdf_path and abstract_text:
                        yield json.dumps({"type": "log", "content": f"📝 요약 생성 중 (PDF 없음): {p.title[:30]}..."}, ensure_ascii=False) + "\n"
                        summary_text = generate_abstract_summary(p.title, abstract_text)
                        if summary_text:
                            # [초록] + [구분자] + [요약] 형태로 저장
                            final_abstract = f"{abstract_text}{SUMMARY_MARKER}{summary_text}"

                    staged = StagedPaper(
                        session_id=session_id, user_email=email, source="pubmed",
                        title=p.title, authors=", ".join(p.authors) if p.authors else "",
                        year=p.year, 
                        url=getattr(p, "url", None) or f"https://pubmed.ncbi.nlm.nih.gov/{p.pmid}/",
                        abstract=final_abstract, 
                        score=getattr(p, "score", 0.0),
                        pdf_storage_path=pdf_path
                        # summary 인자 삭제 (오류 방지)
                    )
                    db.add(staged)
                    saved_models.append(staged)
                
                db.commit()

                paper_list = "\n".join([f"{i+1}. [{p.title}]({p.url}) {'✅(PDF)' if p.pdf_storage_path else '📝(요약)'}" for i, p in enumerate(saved_models)])
                final_content = f"✅ **검색 완료**: {len(saved_models)}건 적재 (PDF 확보: {success_count}건)\n\n{paper_list}"
                
                db.add(Message(session_id=session_id, user_email=email, role="ai", content=final_content))
                db.commit()

                result_data = [
                    {
                        "id": str(p.id), "title": p.title, "year": p.year, "source": p.source,
                        "url": p.url, "has_pdf": bool(p.pdf_storage_path) 
                    } 
                    for p in saved_models
                ]
                yield json.dumps({"type": "result", "content": final_content, "data": result_data}, ensure_ascii=False) + "\n"
            
            else:
                msg = "검색 결과가 없습니다. 키워드를 변경하여 다시 시도해 보세요."
                db.add(Message(session_id=session_id, user_email=email, role="ai", content=msg))
                db.commit()
                yield json.dumps({"type": "message", "content": msg}, ensure_ascii=False) + "\n"

        except Exception as e:
            print(f"[Research Stream Error] {e}")
            yield json.dumps({"type": "error", "content": f"시스템 오류: {str(e)}"}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@router.get("/{session_id}/research/candidates")
def list_candidates(session_id: UUID, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    papers = db.query(StagedPaper).filter(StagedPaper.session_id == session_id, StagedPaper.user_email == email).order_by(StagedPaper.created_at.desc()).all()
    
    results = []
    for p in papers:
        # ✅ [수정] 프론트엔드 목록/분석 탭에는 순수 초록만 전달 (구분자 앞부분)
        raw_abstract = p.abstract or ""
        clean_abstract = raw_abstract.split(SUMMARY_MARKER)[0]
        
        results.append({
            "id": str(p.id),
            "title": p.title,
            "source": p.source,
            "year": p.year,
            "authors": p.authors,
            "url": p.url,
            "abstract": clean_abstract, # 요약 부분 잘라내고 전달
            "score": p.score,
            "has_pdf": bool(p.pdf_storage_path and os.path.exists(p.pdf_storage_path)),
            "created_at": p.created_at
        })
    return results

@router.get("/{session_id}/papers/{paper_id}/download")
def download_paper_pdf(
    session_id: UUID,
    paper_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    paper = db.query(StagedPaper).filter(StagedPaper.id == paper_id, StagedPaper.session_id == session_id).first()
    
    if not paper: raise HTTPException(404, "Paper not found")
    if not paper.pdf_storage_path or not os.path.exists(paper.pdf_storage_path):
        raise HTTPException(404, "PDF file not available on server")

    return FileResponse(
        path=paper.pdf_storage_path,
        filename=f"{paper.title[:50]}.pdf",
        media_type="application/pdf"
    )

@router.get("/{session_id}/papers/{paper_id}/summary")
def get_paper_summary(
    session_id: UUID,
    paper_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    논문 요약 반환 (uploaded_file의 응답 규격과 100% 일치시킴)
    """
    paper = db.query(StagedPaper).filter(StagedPaper.id == paper_id, StagedPaper.session_id == session_id).first()
    
    if not paper:
        raise HTTPException(404, "Paper not found")
    
    # DB의 abstract 필드에서 마커 뒤에 숨겨둔 요약본 추출
    raw_content = paper.abstract or ""
    parts = raw_content.split(SUMMARY_MARKER)
    
    if len(parts) > 1:
        return {
            "status": "done", 
            "content": parts[1].strip() 
        }
    
    # 요약이 없으면 업로드 파일 처리 방식처럼 안내 텍스트 송출
    return {
        "status": "empty", 
        "content": "### 요약 보고서 없음\n현재 이 논문에 대한 상세 분석 데이터가 존재하지 않습니다." 
    }