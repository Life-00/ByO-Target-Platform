from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user_email

from app.models.pipeline import Selection
from app.schemas.selections import (
    SelectionsUpsertRequest,
    SelectionResponse,
    SelectionItem,
)

router = APIRouter(prefix="/sessions", tags=["selections"])


@router.get("/{session_id}/selections", response_model=list[SelectionResponse])
async def list_selections(
    session_id: UUID,  # ✅ UUID 타입 적용
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .order_by(Selection.created_at.desc())
        .all()
    )
    return rows


@router.put("/{session_id}/selections", response_model=list[SelectionResponse])
async def sync_selections(
    session_id: UUID,  # ✅ UUID 타입 적용
    payload: SelectionsUpsertRequest,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    # 1) 현재 DB 상태
    existing = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .all()
    )

    # item_id는 DB에서 UUID이므로 그대로 사용
    existing_set = {(e.item_type, e.item_id) for e in existing}

    # 2) 요청 상태
    req_set = set()
    for item in payload.items:
        if item.item_type not in ("uploaded_file", "staged_paper"):
            raise HTTPException(status_code=400, detail=f"지원하지 않는 item_type: {item.item_type}")
        # item.item_id는 Schema에서 UUID로 정의됨
        req_set.add((item.item_type, item.item_id))

    # 3) 삭제 대상
    to_delete = existing_set - req_set
    if to_delete:
        delete_rows = [e for e in existing if (e.item_type, e.item_id) in to_delete]
        for r in delete_rows:
            db.delete(r)

    # 4) 추가 대상
    to_add = req_set - existing_set
    for item_type, item_id in to_add:
        rec = Selection(
            session_id=session_id,
            user_email=email,
            item_type=item_type,
            item_id=item_id,
        )
        db.add(rec)

    db.commit()

    rows = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .order_by(Selection.created_at.desc())
        .all()
    )
    return rows


@router.post("/{session_id}/selections/toggle", response_model=list[SelectionResponse])
async def toggle_selection(
    session_id: UUID,  # ✅ UUID 타입 적용
    item: SelectionItem,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    if item.item_type not in ("uploaded_file", "staged_paper"):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 item_type: {item.item_type}")

    row = (
        db.query(Selection)
        .filter(
            Selection.session_id == session_id,
            Selection.user_email == email,
            Selection.item_type == item.item_type,
            Selection.item_id == item.item_id, # 둘 다 UUID
        )
        .first()
    )

    if row:
        db.delete(row)
    else:
        db.add(
            Selection(
                session_id=session_id,
                user_email=email,
                item_type=item.item_type,
                item_id=item.item_id,
            )
        )

    db.commit()

    rows = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .order_by(Selection.created_at.desc())
        .all()
    )
    return rows