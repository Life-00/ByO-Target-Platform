from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.report import ReportRequest, ReportResponse
from app.service.rag_service import rag_service
from app.service.solar_service import solar_service

router = APIRouter(prefix="/sessions", tags=["report"])

@router.post("/{session_id}/report", response_model=ReportResponse)
async def create_report(
    session_id: UUID,  # ✅ UUID 타입 적용
    payload: ReportRequest, 
    email: str = Depends(get_current_user_email), 
    db: Session = Depends(get_db)
):
    # 서비스 계층 호출 시 문자열 변환
    ctx = await rag_service.get_relevant_context(payload.prompt, str(session_id), email)
    message = f"다음 컨텍스트를 참고해서 보고서를 작성해줘.\n\n[CONTEXT]\n{ctx}\n\n[REQUEST]\n{payload.prompt}"

    reply = await solar_service.get_chat_response(
        user_email=email, 
        message=message, 
        session_id=str(session_id),  # ✅ str() 변환
        history=[]
    )
    return {"session_id": session_id, "content": reply}