from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.models.chat import ChatSession, Message
from app.schemas.sessions import SessionCreate, SessionResponse
from app.schemas.messages import MessageResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("", response_model=list[SessionResponse])
async def list_sessions(email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    return db.query(ChatSession).filter(ChatSession.user_email == email).order_by(ChatSession.created_at.desc()).all()

@router.post("", response_model=SessionResponse)
async def create_session(payload: SessionCreate, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    s = ChatSession(user_email=email, title=payload.title)
    db.add(s)
    db.flush()
    db.add(Message(session_id=s.id, user_email=email, role="ai", content="새로운 분석 세션입니다. 분석할 파일이 있다면 첨부해 주세요."))
    db.commit()
    db.refresh(s)
    return s

@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    return db.query(Message).filter(Message.session_id == session_id, Message.user_email == email).order_by(Message.created_at.asc()).all()

@router.delete("/{session_id}")
async def delete_session(session_id: str, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_email == email).first()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    db.delete(session)
    db.commit()
    return {"message": "Deleted"}
