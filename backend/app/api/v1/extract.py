from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user_email

from app.models.pipeline import Selection, UploadedFile, VectorIndexRecord
from app.service.rag_service import rag_service
from app.schemas.extract import ExtractResponse


router = APIRouter(prefix="/sessions", tags=["extract"])


@router.post("/{session_id}/extract", response_model=ExtractResponse)
async def run_extract(
    session_id: UUID,  # ✅ UUID 타입 적용
    force: bool = False,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    - selections에 있는 항목들 중 uploaded_file만 인덱싱
    - 이미 VectorIndexRecord가 success인 파일은 재인덱싱하지 않음
    - force=true면 success여도 재인덱싱 시도
    """

    # 1) 선택 목록 로드
    selections = (
        db.query(Selection)
        .filter(Selection.session_id == session_id, Selection.user_email == email)
        .all()
    )

    if not selections:
        return {"session_id": session_id, "results": []}

    results = []

    # 2) uploaded_file만 처리
    for s in selections:
        if s.item_type != "uploaded_file":
            continue

        # Selection.item_id는 DB에서 UUID 타입임
        uf = (
            db.query(UploadedFile)
            .filter(
                UploadedFile.id == s.item_id,
                UploadedFile.session_id == session_id,
                UploadedFile.user_email == email,
            )
            .first()
        )

        if not uf:
            results.append(
                {
                    "item_type": "uploaded_file",
                    "item_id": s.item_id, # UUID 객체
                    "status": "missing",
                    "error": "선택된 파일을 DB에서 찾을 수 없습니다.",
                }
            )
            continue

        # 3) 중복 인덱싱 방지
        existing_success = (
            db.query(VectorIndexRecord)
            .filter(
                VectorIndexRecord.session_id == session_id,
                VectorIndexRecord.user_email == email,
                VectorIndexRecord.item_type == "uploaded_file",
                VectorIndexRecord.item_id == uf.id,
                VectorIndexRecord.status == "success",
            )
            .first()
        )

        if existing_success and not force:
            results.append(
                {
                    "item_type": "uploaded_file",
                    "item_id": uf.id,
                    "status": "skipped",
                }
            )
            continue

        # 4) 인덱싱 레코드 생성 (running)
        idx = VectorIndexRecord(
            session_id=session_id,
            user_email=email,
            item_type="uploaded_file",
            item_id=uf.id,
            chroma_collection=f"session_{session_id}",
            embedding_model=None,
            status="running",
            stats=None,
        )
        db.add(idx)
        db.commit()
        db.refresh(idx)

        # 5) 실제 인덱싱 수행
        try:
            # ✅ 서비스 호출 시에는 str()로 명시적 변환
            ret = await rag_service.process_and_store(
                file_path=uf.storage_path,
                session_id=str(session_id),
                email=email,
                file_id=str(uf.id),
                collection_name=f"session_{session_id}",
                upsert=force,
            )

            if not ret.get("ok"):
                idx.status = "fail"
                idx.stats = {"error": ret.get("error", "unknown")}
                db.commit()

                results.append(
                    {
                        "item_type": "uploaded_file",
                        "item_id": uf.id,
                        "status": "fail",
                        "error": ret.get("error", "unknown"),
                    }
                )
                continue

            idx.status = "success"
            idx.stats = {
                "chunk_count": ret.get("chunk_count", 0),
                "skipped_all": ret.get("skipped_all", False),
                "force": force,
            }
            
            uf.status = "indexed" 
            db.add(uf)
            
            db.commit()

            results.append(
                {
                    "item_type": "uploaded_file",
                    "item_id": uf.id,
                    "status": "success" if not ret.get("skipped_all") else "success_noop",
                }
            )

        except Exception as e:
            idx.status = "fail"
            idx.stats = {"error": str(e)}
            db.commit()

            results.append(
                {
                    "item_type": "uploaded_file",
                    "item_id": uf.id,
                    "status": "fail",
                    "error": str(e),
                }
            )

    return {"session_id": session_id, "results": results}