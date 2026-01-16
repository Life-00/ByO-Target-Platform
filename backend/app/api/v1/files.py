# app/api/v1/files.py
import os
import uuid
import shutil
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email

from app.models.pipeline import UploadedFile
from app.schemas.files import FileUploadResponse, UploadedFileResponse
# [NEW] 자동 추출 함수 import
from app.api.v1.extract import auto_extract_file

router = APIRouter(prefix="/sessions", tags=["files"])

# 업로드 저장 디렉토리
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 허용 확장자
ALLOWED_EXTS = {
    ".pdf", ".txt", ".md",
    ".docx", ".pptx",
    ".csv", ".xlsx",
    ".png", ".jpg", ".jpeg",
}

MAX_FILE_SIZE_MB = 50


def _safe_ext(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lower()


def _build_storage_path(session_id: str, file_id: uuid.UUID, original_name: str) -> str:
    # 파일명이 이상해도 안전한 저장명을 쓰는 게 좋음
    ext = _safe_ext(original_name)
    safe_name = f"{session_id}_{file_id.hex}{ext}"
    return os.path.join(UPLOAD_DIR, safe_name)


@router.post("/{session_id}/files", response_model=List[FileUploadResponse])
async def upload_files(
    session_id: UUID,  # ✅ UUID 타입 적용
    files: Optional[List[UploadFile]] = File(None),
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(), # ✅ BackgroundTasks 주입
):
    """
    ✅ 업로드 -> 저장 -> DB기록 -> (백그라운드) 자동 추출 및 벡터화
    """
    if not files:
        return []

    results: List[FileUploadResponse] = []

    for f in files:
        if not f.filename:
            results.append({"file_id": uuid.uuid4(), "original_name": "", "status": "failed"})
            continue

        ext = _safe_ext(f.filename)
        if ext and ALLOWED_EXTS and ext not in ALLOWED_EXTS:
            results.append({"file_id": uuid.uuid4(), "original_name": f.filename, "status": "rejected"})
            continue

        file_id = uuid.uuid4()
        # ✅ session_id는 UUID 객체이므로 str()로 변환하여 경로 생성
        save_path = _build_storage_path(str(session_id), file_id, f.filename)

        # 파일 크기 체크(스트리밍 방식)
        total = 0
        try:
            with open(save_path, "wb") as buffer:
                while True:
                    chunk = await f.read(1024 * 1024)  # 1MB
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_FILE_SIZE_MB * 1024 * 1024:
                        raise HTTPException(status_code=413, detail=f"파일이 너무 큽니다. (최대 {MAX_FILE_SIZE_MB}MB)")
                    buffer.write(chunk)
        except Exception as e:
            # 저장 실패 시 파일 제거
            try:
                if os.path.exists(save_path):
                    os.remove(save_path)
            except Exception:
                pass

            results.append({"file_id": file_id, "original_name": f.filename, "status": "failed"})
            continue
        finally:
            try:
                await f.close()
            except Exception:
                pass

        # DB 기록 생성
        rec = UploadedFile(
            id=file_id,
            session_id=session_id, # SQLAlchemy가 UUID 객체 처리
            user_email=email,
            original_name=f.filename,
            storage_path=save_path,
            mime_type=f.content_type,
            size_bytes=total,
            status="uploaded", # 초기 상태: 업로드됨
        )
        db.add(rec)
        db.commit()

        # ✅ [핵심] 백그라운드 작업 등록: 자동 추출 실행
        # 파일이 성공적으로 저장된 경우에만 실행
        background_tasks.add_task(
            auto_extract_file,
            session_id=session_id,
            file_id=file_id,
            user_email=email
        )

        results.append({"file_id": file_id, "original_name": f.filename, "status": "uploaded"})

    return results


@router.get("/{session_id}/files", response_model=List[UploadedFileResponse])
async def list_files(
    session_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(UploadedFile)
        .filter(UploadedFile.session_id == session_id, UploadedFile.user_email == email)
        .order_by(UploadedFile.created_at.desc())
        .all()
    )
    return rows


@router.delete("/{session_id}/files/{file_id}")
async def delete_file(
    session_id: UUID,
    file_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id == file_id,
            UploadedFile.session_id == session_id,
            UploadedFile.user_email == email,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    # 실제 파일 삭제
    try:
        if row.storage_path and os.path.exists(row.storage_path):
            os.remove(row.storage_path)
    except Exception as e:
        pass

    db.delete(row)
    db.commit()

    return {"message": "deleted", "file_id": file_id}


@router.get("/{session_id}/files/{file_id}/download")
async def download_file(
    session_id: UUID,
    file_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id == file_id,
            UploadedFile.session_id == session_id,
            UploadedFile.user_email == email,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    if not row.storage_path or not os.path.exists(row.storage_path):
        raise HTTPException(status_code=404, detail="서버에 파일이 존재하지 않습니다.")

    return FileResponse(
        path=row.storage_path,
        filename=row.original_name,
        media_type=row.mime_type or "application/octet-stream",
    )
    
@router.get("/{session_id}/files/{file_id}/summary")
async def get_file_summary(
    session_id: UUID,
    file_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    파일의 요약본(summary 컬럼)을 반환합니다.
    """
    uf = db.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.session_id == session_id,
        UploadedFile.user_email == email
    ).first()

    if not uf:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not uf.summary:
        # 아직 요약이 안 된 경우
        if uf.status == "uploaded":
            return {"status": "processing", "content": "🔄 문서를 분석하고 요약 보고서를 작성 중입니다... 잠시만 기다려 주세요."}
        else:
            return {"status": "empty", "content": "요약된 내용이 없습니다."}

    return {"status": "done", "content": uf.summary}