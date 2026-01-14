import json
import uuid
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.research import ResearchRequest, StagedPaperResponse
from app.models.pipeline import StagedPaper
from app.models.chat import Message

# Agent & Schema
from app.agents.retriever.agent import RetrieverAgent
from app.schemas.query import UserQuery
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

# ----------------------------------------------------------------
# 사용자 자연어 분석 함수
# ----------------------------------------------------------------
def analyze_user_input(user_text: str, history: List[dict] = None) -> dict:
    # 대화 기록을 문자열로 변환 (최근 5개만)
    history_text = ""
    if history:
        for msg in history[-5:]:
            role = "User" if msg['role'] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"
    
    prompt = f"""
    You are a specialized Query Analyst for a Biomedical Research Agent.
    
    [Conversation History]
    {history_text or "No previous conversation."}
    
    [Latest User Input]
    "{user_text}"
    
    Task:
    1. Analyze the 'Latest User Input' in the context of 'Conversation History'.
    2. The user might refer to previous topics (e.g., "how about its side effects?").
    3. HOWEVER, prioritize the 'Latest User Input' as the main intent.
    4. Extract structured information.
    5. Translate Korean query to English biomedical terms.
    
    Output JSON format ONLY:
    {{
        "is_clear": true/false,
        "missing_info": "...",
        "intent": "...",
        "target": "...",
        "disease": "..."
    }}
    """
    try:
        response = call_llm(prompt, temperature=0)
        
        # JSON 추출 로직 (앞뒤 군더더기 제거)
        start_idx = response.find("{")
        end_idx = response.rfind("}")
        
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx : end_idx + 1]
            return json.loads(json_str)
        else:
            print(f"[Query Analysis Fail] No JSON found in: {response}")
            return {"is_clear": True, "intent": user_text}
            
    except Exception as e:
        print(f"[Query Analysis Error] {e}")
        return {"is_clear": True, "intent": user_text}

# ----------------------------------------------------------------
# Research 엔드포인트 (동기 방식 Streaming)
# ----------------------------------------------------------------
# ⚠️ 중요: async def가 아닌 def로 선언해야 동기 제너레이터가 스레드풀에서 돌며 스트리밍됨
@router.post("/{session_id}/research")
def research(
    session_id: UUID, 
    payload: ResearchRequest, 
    email: str = Depends(get_current_user_email), 
    db: Session = Depends(get_db)
):
    # 1. 사용자 질문 저장 (최초 요청 시에만)
    if not payload.is_confirmed:
        user_msg = Message(
            session_id=session_id,
            user_email=email,
            role="user",
            content=payload.query
        )
        db.add(user_msg)
        db.commit()

    # 내부 제너레이터 함수도 동기(def)로 변경
    def event_generator():
        try:
            # ====================================================
            # 🛑 CASE 1: 분석 및 제안 (Proposal)
            # ====================================================
            if not payload.is_confirmed:
                yield json.dumps({"type": "log", "content": "🤔 사용자의 의도를 분석하고 있습니다..."}, ensure_ascii=False) + "\n"
                
                # 대화 이력 가져오기 (Context-Aware)
                recent_messages = (
                    db.query(Message)
                    .filter(Message.session_id == session_id)
                    .order_by(Message.created_at.desc())
                    .limit(10)
                    .all()
                )
                history = [{"role": m.role, "content": m.content} for m in reversed(recent_messages)]
                
                # ✅ [수정] history를 전달하여 분석
                analysis = analyze_user_input(payload.query, history)
                
                if not analysis.get("is_clear", True):
                    msg = analysis.get("missing_info", "정보가 부족합니다.")
                    yield json.dumps({"type": "error", "content": f"[정보 부족] {msg}"}, ensure_ascii=False) + "\n"
                    return

                # 제안 메시지 생성
                proposal_msg = (
                    f"**[검색 의도 확인]**\n\n"
                    f"🔹 **주제**: {analysis.get('intent')}\n"
                    f"🔹 **타겟**: {analysis.get('target') or '없음'}\n"
                    f"🔹 **질환**: {analysis.get('disease') or '없음'}\n\n"
                    f"이 내용으로 논문을 검색할까요?"
                )
                
                yield json.dumps({
                    "type": "proposal",
                    "content": proposal_msg,
                    "analysis": analysis
                }, ensure_ascii=False) + "\n"
                return

            # ====================================================
            # 🚀 CASE 2: 실제 검색 수행 (Execution)
            # ====================================================
            confirmed_data = payload.confirmed_intent or {}
            final_intent = confirmed_data.get("intent", payload.query)
            
            # 로그 전송
            yield json.dumps({"type": "log", "content": f"🚀 검색 시작: {final_intent}"}, ensure_ascii=False) + "\n"

            user_query = UserQuery(
                query_id=str(uuid.uuid4()),
                intent=final_intent,
                target_hint=confirmed_data.get("target"), 
                disease=confirmed_data.get("disease"),
                organ=confirmed_data.get("organ")
            )

            # Agent 파이프라인 실행 (여기서 동기 함수들이 실행됨 -> 스레드풀 사용)
            final_corpus = None
            for step_data in retriever_agent.run_stream(user_query):
                if step_data["type"] == "log":
                    yield json.dumps(step_data, ensure_ascii=False) + "\n"
                elif step_data["type"] == "result":
                    final_corpus = step_data["data"]

            # DB 저장 및 결과 전송
            if final_corpus and final_corpus.papers:
                final_papers = final_corpus.papers[:payload.top_k]
                saved_models = []
                
                for p in final_papers:
                    abstract_text = " ".join([s.text for s in p.abstract_sentences]) if p.abstract_sentences else ""
                    
                    staged = StagedPaper(
                        session_id=session_id,
                        user_email=email,
                        source="pubmed",
                        title=p.title,
                        authors=", ".join(p.authors) if p.authors else "",
                        year=p.year,
                        url=p.url if hasattr(p, "url") and p.url else f"https://pubmed.ncbi.nlm.nih.gov/{p.pmid}/",
                        abstract=abstract_text,
                        score=p.score if hasattr(p, "score") else 0.0
                    )
                    db.add(staged)
                    saved_models.append(staged)
                
                db.commit()

                ai_content = f"✅ 검색 완료: 총 {len(saved_models)}건의 논문을 찾았습니다."
                ai_msg = Message(
                    session_id=session_id,
                    user_email=email,
                    role="ai",
                    content=ai_content
                )
                db.add(ai_msg)
                db.commit()

                result_data = [
                    {
                        "id": str(p.id),
                        "title": p.title,
                        "source": p.source,
                        "year": p.year,
                        "authors": p.authors,
                        "score": p.score,
                        "url": p.url
                    } 
                    for p in saved_models
                ]
                yield json.dumps({"type": "result", "data": result_data}, ensure_ascii=False) + "\n"
            else:
                yield json.dumps({"type": "error", "content": "검색 결과가 없습니다."}, ensure_ascii=False) + "\n"

        except Exception as e:
            print(f"[Stream Error] {e}")
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_generator(), 
        media_type="application/x-ndjson",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/{session_id}/research/candidates", response_model=list[StagedPaperResponse])
def list_candidates(
    session_id: UUID, 
    email: str = Depends(get_current_user_email), 
    db: Session = Depends(get_db)
):
    return db.query(StagedPaper).filter(
        StagedPaper.session_id == session_id, 
        StagedPaper.user_email == email
    ).order_by(StagedPaper.created_at.desc()).all()