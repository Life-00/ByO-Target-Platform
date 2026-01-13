from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.research import ResearchRequest, StagedPaperResponse
from app.models.pipeline import StagedPaper

router = APIRouter(prefix="/sessions", tags=["research"])

@router.post("/{session_id}/research", response_model=list[StagedPaperResponse])
async def research(
    session_id: UUID,  # ✅ UUID 타입 적용
    payload: ResearchRequest, 
    email: str = Depends(get_current_user_email), 
    db: Session = Depends(get_db)
):
    candidates = []
    for i in range(payload.top_k):
        p = StagedPaper(
            session_id=session_id,
            user_email=email,
            source="stub",
            title=f"[stub] {payload.query} candidate {i+1}",
            authors=None,
            year=None,
            url=None,
            abstract=None,
            score=None,
        )
        db.add(p)
        candidates.append(p)
    db.commit()
    return candidates

@router.get("/{session_id}/research/candidates", response_model=list[StagedPaperResponse])
async def list_candidates(
    session_id: UUID,  # ✅ UUID 타입 적용
    email: str = Depends(get_current_user_email), 
    db: Session = Depends(get_db)
):
    return db.query(StagedPaper).filter(StagedPaper.session_id == session_id, StagedPaper.user_email == email).order_by(StagedPaper.created_at.desc()).all()