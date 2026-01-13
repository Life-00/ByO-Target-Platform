import time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import oauth2_scheme
from app.service.auth_service import auth_service
from app.service.solar_service import solar_service
from app.service.rag_service import rag_service

from app.models.chat import ChatSession, Message
from app.schemas.chat import ChatRequest

router = APIRouter()

@router.post("/sessions/{session_id}/chat")
async def session_chat(
    session_id: UUID,       # ✅ UUID 타입으로 받음
    payload: ChatRequest,   # ✅ JSON Body (message, context_ids)
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    print(f"\n[{time.strftime('%H:%M:%S')}] [CHAT] Session: {session_id}")

    email = auth_service.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")

    # 세션 확인
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_email == email)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    # 1) 유저 메시지 저장
    user_msg = Message(
        session_id=session_id, 
        user_email=email, 
        role="user", 
        content=payload.message
    )
    db.add(user_msg)
    db.commit()

    # 2) RAG: 선택된 파일이 있다면 내용 검색 (또는 요약 데이터 가져오기)
    context_text = ""
    if payload.context_ids:
        try:
            # Pydantic이 문자열 리스트로 줄 수도 있으므로 안전하게 UUID 변환
            # (이미 UUID 리스트라면 str() 했다가 다시 UUID() 해도 안전함)
            file_uuids = [UUID(str(fid)) for fid in payload.context_ids]
            
            context_text = await rag_service.get_relevant_context(
                query=payload.message,
                session_id=session_id,  # ✅ UUID 객체 그대로 전달
                email=email,
                file_ids=file_uuids     # ✅ 체크된 파일 ID 전달
            )
            print(f"[RAG] Retrieved context length: {len(context_text)}")
        except Exception as e:
            print(f"[RAG Error] {e}")

    # 3) 대화 히스토리 로드
    history_records = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )
    history_records.reverse()
    chat_history = [{"role": m.role, "content": m.content} for m in history_records]

    # 4) LLM 호출
    # 시스템 프롬프트 조립은 solar_service 내부에서 수행
    reply = await solar_service.get_chat_response(
        user_email=email,
        message=payload.message, 
        session_id=session_id,  # ✅ UUID 객체 그대로 전달
        history=chat_history,
        context=context_text    # ✅ 검색된 내용(문맥) 전달
    )

    # 5) AI 메시지 저장
    db.add(Message(session_id=session_id, user_email=email, role="ai", content=reply))
    db.commit()

    return {"reply": reply}