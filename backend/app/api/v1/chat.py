import time
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import oauth2_scheme
from app.service.auth_service import auth_service
from app.service.solar_service import solar_service

# models/ 정리 완료 기준
from app.models.chat import ChatSession, Message

router = APIRouter()


@router.post("/sessions/{session_id}/chat")
async def session_chat(
    session_id: str,
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    print(f"\n[{time.strftime('%H:%M:%S')}] [CHAT] Session: {session_id}")

    email = auth_service.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")

    # ✅ 규칙: 업로드/벡터화는 chat에서 금지
    if files:
        raise HTTPException(
            status_code=400,
            detail="파일 업로드는 /sessions/{session_id}/files 로 요청하세요. (chat에서는 업로드/벡터화를 지원하지 않습니다.)",
        )

    # 세션 존재 확인(본인 세션만)
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_email == email)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    # 1) 유저 메시지 저장
    user_msg = Message(session_id=session_id, user_email=email, role="user", content=message)
    db.add(user_msg)
    db.commit()

    # 2) 최근 대화 히스토리 로드(토큰/비용 고려해서 20개)
    history_records = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )
    history_records.reverse()

    chat_history = [{"role": m.role, "content": m.content} for m in history_records]

    # 3) LLM 응답 생성 (일반 대화 모드)
    reply = await solar_service.get_chat_response(
        user_email=email,
        message=message,
        session_id=session_id,
        history=chat_history,
    )

    # 4) AI 메시지 저장
    db.add(Message(session_id=session_id, user_email=email, role="ai", content=reply))
    db.commit()

    return {"reply": reply}
