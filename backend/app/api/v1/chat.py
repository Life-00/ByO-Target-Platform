import os
import time
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user_db import ChatSession, Message
from app.api.v1.auth import oauth2_scheme
from app.service.auth_service import auth_service
from app.service.solar_service import solar_service
from app.service.rag_service import rag_service
from pydantic import BaseModel

router = APIRouter()

class TitleUpdate(BaseModel):
    title: str

# 파일 저장 경로 설정
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 1. 세션 목록 조회
@router.get("/sessions")
async def get_sessions(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = auth_service.verify_token(token)
    return db.query(ChatSession).filter(ChatSession.user_email == email).order_by(ChatSession.created_at.desc()).all()

# 2. 새 세션 생성
@router.post("/sessions")
async def create_session(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = auth_service.verify_token(token)
    new_session = ChatSession(user_email=email, title="새로운 분석 세션")
    db.add(new_session)
    db.flush()
    db.add(Message(session_id=new_session.id, user_email=email, role="ai", content="새로운 분석 세션입니다. 분석할 파일이 있다면 첨부해 주세요."))
    db.commit()
    db.refresh(new_session)
    return new_session

# 3. 세션 제목 업데이트
@router.patch("/sessions/{session_id}")
async def update_session_title(session_id: str, payload: TitleUpdate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = auth_service.verify_token(token)
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_email == email).first()
    if not session: raise HTTPException(status_code=404)
    session.title = payload.title
    db.commit()
    return {"status": "success"}

# 4. 세션 메시지 조회
@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = auth_service.verify_token(token)
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()

# 5. 통합 채팅 및 파일 업로드
@router.post("/sessions/{session_id}/chat")
async def session_chat(
    session_id: str,
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    print(f"\n[{time.strftime('%H:%M:%S')}] [CHAT-REQUEST] Session: {session_id}")
    email = auth_service.verify_token(token)

    # 1. 파일이 있으면 분석 및 벡터 DB 저장 (RAG) - [기존 코드 유지]
    if files:
        for file in files:
            file_uuid = uuid.uuid4().hex[:8]
            file_name = f"{session_id}_{file_uuid}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, file_name)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            print(f"[{time.strftime('%H:%M:%S')}] [RAG] Processing file: {file.filename}")
            await rag_service.process_and_store(file_path, session_id, email)

    # 2. 유저 메시지 DB 저장 (현재 메시지 저장) - [기존 코드 유지]
    current_msg = Message(session_id=session_id, user_email=email, role="user", content=message)
    db.add(current_msg)
    db.commit() # DB에 저장 확정 (그래야 아래에서 조회됨)
    
    # [수정] 대화 맥락(Context) 불러오기
    # 최근 20개의 대화를 가져옵니다 (토큰 제한 고려).
    history_records = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(20).all()
    
    # 시간순 정렬 (오래된 것 -> 최신 것)
    history_records.reverse()
    
    # 서비스에 넘길 형태로 변환 (List[dict])
    chat_history = [
        {"role": msg.role, "content": msg.content} 
        for msg in history_records
    ]

    # 3. Solar-Pro 답변 생성 (history 인자 추가)
    # 기존: reply = await solar_service.get_chat_response(email, message, session_id=session_id)
    reply = await solar_service.get_chat_response(
        user_email=email, 
        message=message, 
        session_id=session_id,
        history=chat_history 
    )
    
    # 4. AI 답변 DB 저장 - [기존 코드 유지]
    db.add(Message(session_id=session_id, user_email=email, role="ai", content=reply))
    db.commit()
    
    return {"reply": reply}

# 6. 세션 삭제
@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = auth_service.verify_token(token)
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_email == email).first()
    if not session: raise HTTPException(status_code=404)
    db.delete(session)
    db.commit()
    return {"message": "Deleted"}