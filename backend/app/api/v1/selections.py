from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_

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
    session_id: str,
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
    session_id: str,
    payload: SelectionsUpsertRequest,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    프론트가 '최종 선택 목록'을 보내면,
    DB에 있는 기존 선택과 비교해서:
      - 없는 것은 삭제
      - 새로운 것은 추가
    로 동기화한다 (idempotent).
    """

    # 1) 현재 DB 상태
    existing = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .all()
    )

    existing_set = {(e.item_type, str(e.item_id)) for e in existing}

    # 2) 요청 상태(중복 제거)
    req_set = set()
    for item in payload.items:
        if item.item_type not in ("uploaded_file", "staged_paper"):
            raise HTTPException(status_code=400, detail=f"지원하지 않는 item_type: {item.item_type}")
        req_set.add((item.item_type, str(item.item_id)))

    # 3) 삭제 대상
    to_delete = existing_set - req_set
    if to_delete:
        # 여러 조건 OR로 처리하지 않고, 파이썬에서 id 뽑아서 delete
        delete_rows = [e for e in existing if (e.item_type, str(e.item_id)) in to_delete]
        for r in delete_rows:
            db.delete(r)

    # 4) 추가 대상
    to_add = req_set - existing_set
    inserted = []
    for item_type, item_id in to_add:
        rec = Selection(
            session_id=session_id,
            user_email=email,
            item_type=item_type,
            item_id=item_id,
        )
        db.add(rec)
        inserted.append(rec)

    db.commit()

    # 5) 최신 상태 반환
    rows = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .order_by(Selection.created_at.desc())
        .all()
    )
    return rows


@router.post("/{session_id}/selections/toggle", response_model=list[SelectionResponse])
async def toggle_selection(
    session_id: str,
    item: SelectionItem,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    체크박스 한 번 클릭할 때마다 호출 가능.
    존재하면 삭제(언체크), 없으면 추가(체크).
    """

    if item.item_type not in ("uploaded_file", "staged_paper"):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 item_type: {item.item_type}")

    row = (
        db.query(Selection)
        .filter(
            Selection.session_id == session_id,
            Selection.user_email == email,
            Selection.item_type == item.item_type,
            Selection.item_id == item.item_id,
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
