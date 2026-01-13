from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.research import ResearchRequest, StagedPaperResponse
from app.models.pipeline import StagedPaper

router = APIRouter(prefix="/sessions", tags=["research"])

@router.post("/{session_id}/research", response_model=list[StagedPaperResponse])
async def research(session_id: str, payload: ResearchRequest, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    # TODO: 실제 retrieval agent 붙이면 여기 교체
    # 지금은 더미 후보군 생성
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
async def list_candidates(session_id: str, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    return db.query(StagedPaper).filter(StagedPaper.session_id == session_id, StagedPaper.user_email == email).order_by(StagedPaper.created_at.desc()).all()
