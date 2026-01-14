# app/api/v1/chat.py

import time
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import oauth2_scheme
from app.service.auth_service import auth_service
from app.service.solar_service import solar_service
from app.service.rag_service import rag_service

from app.models.chat import ChatSession, Message
from app.models.pipeline import UploadedFile, StagedPaper, Selection
from app.schemas.chat import ChatRequest

router = APIRouter()


def _safe_uuid(x: Any) -> Optional[UUID]:
    try:
        return UUID(str(x))
    except Exception:
        return None


def _build_context_items_from_ids(
    db: Session,
    ids: List[UUID],
) -> List[Dict[str, str]]:
    """
    context_ids / Selection.item_id 로부터 실제 대상(UploadedFile/StagedPaper)을 찾아
    context_items 형태의 dict list로 복원
    """
    items: List[Dict[str, str]] = []
    for fid in ids:
        uf = db.query(UploadedFile).filter(UploadedFile.id == fid).first()
        if uf:
            items.append(
                {
                    "id": str(uf.id),
                    "type": "uploaded_file",
                    "status": uf.status or "uploaded",
                    "title": uf.original_name or "Untitled File",
                }
            )
            continue

        sp = db.query(StagedPaper).filter(StagedPaper.id == fid).first()
        if sp:
            items.append(
                {
                    "id": str(sp.id),
                    "type": "staged_paper",
                    "status": "staged",
                    "title": sp.title or "Untitled Paper",
                }
            )
            continue

    return items


def _build_context_items_from_selection(
    db: Session,
    session_id: UUID,
    email: str,
) -> List[Dict[str, str]]:
    """
    Selection 테이블(세션 기준 체크박스 상태)에서 item_type+item_id로 복원
    - item_type은 'uploaded_file' | 'staged_paper' 라고 가정(프론트 토글 payload 기준)
    """
    selections = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .all()
    )

    # Selection에 item_type이 있다면 그걸 우선 활용하고, 없으면 id로 추론
    items: List[Dict[str, str]] = []
    for sel in selections:
        sid = sel.item_id
        stype = getattr(sel, "item_type", None)

        # item_type이 있으면 타입별로 조회
        if stype == "uploaded_file":
            uf = db.query(UploadedFile).filter(UploadedFile.id == sid).first()
            if uf:
                items.append(
                    {
                        "id": str(uf.id),
                        "type": "uploaded_file",
                        "status": uf.status or "uploaded",
                        "title": uf.original_name or "Untitled File",
                    }
                )
                continue

        if stype == "staged_paper":
            sp = db.query(StagedPaper).filter(StagedPaper.id == sid).first()
            if sp:
                items.append(
                    {
                        "id": str(sp.id),
                        "type": "staged_paper",
                        "status": "staged",
                        "title": sp.title or "Untitled Paper",
                    }
                )
                continue

        # item_type이 없거나 이상하면: id로 둘 다 조회해서 추론
        uf = db.query(UploadedFile).filter(UploadedFile.id == sid).first()
        if uf:
            items.append(
                {
                    "id": str(uf.id),
                    "type": "uploaded_file",
                    "status": uf.status or "uploaded",
                    "title": uf.original_name or "Untitled File",
                }
            )
            continue

        sp = db.query(StagedPaper).filter(StagedPaper.id == sid).first()
        if sp:
            items.append(
                {
                    "id": str(sp.id),
                    "type": "staged_paper",
                    "status": "staged",
                    "title": sp.title or "Untitled Paper",
                }
            )
            continue

    return items


@router.post("/sessions/{session_id}/chat")
async def session_chat(
    session_id: UUID,
    payload: ChatRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    print(f"\n[{time.strftime('%H:%M:%S')}] [CHAT] Session: {session_id}")

    # 1) 인증
    email = auth_service.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")

    # 2) 세션 확인 (타 유저 세션 접근 방지)
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_email == email)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    # 3) 유저 메시지 저장
    db.add(Message(session_id=session_id, user_email=email, role="user", content=payload.message))
    db.commit()

    # ------------------------------------------------------------------
    # 4) 선택된 아이템 확보 (프론트 → context_ids → DB Selection fallback)
    # ------------------------------------------------------------------
    input_items: List[Dict[str, str]] = []

    # A) 최신 프론트: context_items (가장 신뢰)
    if payload.context_items:
        # pydantic 모델 객체일 수 있으니 dict로 normalize
        for it in payload.context_items:
            input_items.append(
                {
                    "id": str(getattr(it, "id", "")),
                    "type": str(getattr(it, "type", "")),
                    "status": str(getattr(it, "status", "")),
                    "title": str(getattr(it, "title", "")),
                }
            )

    # B) 구버전/일부 프론트: context_ids
    if not input_items and payload.context_ids:
        ids: List[UUID] = []
        for raw in payload.context_ids:
            u = _safe_uuid(raw)
            if u:
                ids.append(u)
        if ids:
            input_items = _build_context_items_from_ids(db, ids)

    # C) 최후: DB Selection (세션 기준 체크 토글 복원)
    if not input_items:
        input_items = _build_context_items_from_selection(db, session_id, email)

    print("[CHAT] raw context_items =", payload.context_items)
    print("[CHAT] context_items len =", len(payload.context_items or []))
    print("[CHAT] resolved input_items len =", len(input_items))

    # ------------------------------------------------------------------
    # 5) RAG 대상 선정 + 시스템 목록 구성
    #    - '선택된 건 전부 컨텍스트'로 인정
    #    - RAG 검색은 indexed/analyzed + uploaded_file만 (안정성)
    # ------------------------------------------------------------------
    rag_file_ids: List[UUID] = []
    system_lines: List[str] = []

    for item in input_items:
        itype = (item.get("type") or "").strip()
        title = (item.get("title") or "").strip() or "(Untitled)"
        status = (item.get("status") or "").strip().lower()

        searchable = (status in ["indexed", "analyzed"]) and (itype == "uploaded_file")

        if searchable:
            status_info = "✅ INDEXED (searchable)"
            uid = _safe_uuid(item.get("id"))
            if uid:
                rag_file_ids.append(uid)
        else:
            # staged_paper / report / not indexed 등은 모두 여기에 들어오게
            status_info = "⏳ NOT INDEXED (not searchable yet)"

        label = itype.upper() if itype else "ITEM"
        system_lines.append(f"- [{label}] {title} ({status_info})")

    selected_count = len(system_lines)
    file_list_str = "\n".join(system_lines)

    # ------------------------------------------------------------------
    # 6) RAG 검색 (가능한 것만)
    # ------------------------------------------------------------------
    retrieved_text = ""
    if rag_file_ids:
        try:
            retrieved_text = await rag_service.get_relevant_context(
                query=payload.message,
                session_id=session_id,
                email=email,
                file_ids=rag_file_ids,
            )
        except Exception as e:
            print(f"[RAG Error] {e}")
            retrieved_text = ""

    # ------------------------------------------------------------------
    # 7) LLM 컨텍스트 강제 주입 (파일/논문/리포트 등 가리지 않고 동일 처리)
    # ------------------------------------------------------------------
    final_context = f"""
    
    ### IMPORTANT: CURRENT SYSTEM STATE
You must ignore all previous file names mentioned in the conversation history.
The ONLY files currently selected and available NOW are listed below.

[CURRENT SELECTED FILES]
{file_list_str}

### INSTRUCTIONS
1. If the user asks for the file name, ONLY refer to the list above.
2. The count of selected items is {selected_count}.
3. Answer based ONLY on the provided context below.

    If Selected items count is 0:
- The user is asking a general question.
- Answer using your general knowledge.
- Do NOT ask the user to select files.
- Do NOT mention Library, checkboxes, or selection requirements.
- If you don't have selected_count, please use your knowledge to answer your questions kindly.

If Selected items count is not 0:
If a selection exists, refer to it, but not unconditionally. Please proceed according to the user's question.

### SYSTEM FACTS (DO NOT GUESS)
Selected items count: {selected_count}

### SELECTED ITEMS (REAL-TIME)
{file_list_str}

- Please tell {file_list_str} regardless of the type


### RETRIEVED CONTEXT (FROM VECTOR DB)
{retrieved_text} 
(Note: Each context chunk is prefixed with [[Page X]]. Use this for citation.)

### RULES
When users ask questions about selected items, follow the following rules

1. **CITATION IS MANDATORY**: When you answer based on the [RETRIEVED CONTEXT], you MUST cite the page number at the end of the sentence.
   - Example: "Meibomian gland dysfunction is a major cause of dry eye [[Page 3]]."
   - Do NOT make up page numbers. Only use what is provided in the context.
   
2. If the user asks "Where is this information?", provide the exact page number.

3. If the answer is not in the context, say "I couldn't find that information in the selected files."

4. Answer in Korean (unless the user asks in English).
"""

    print("[CHAT] context_to_llm preview:\n", final_context[:500])

    # ------------------------------------------------------------------
    # 8) 히스토리 구성 후 LLM 호출
    # ------------------------------------------------------------------
    history_records = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    history_records.reverse()
    chat_history = [{"role": m.role, "content": m.content} for m in history_records]

    reply = await solar_service.get_chat_response(
        user_email=email,
        message=payload.message,
        session_id=session_id,
        history=chat_history,
        context=final_context,
    )

    db.add(Message(session_id=session_id, user_email=email, role="ai", content=reply))
    db.commit()

    return {"reply": reply}
