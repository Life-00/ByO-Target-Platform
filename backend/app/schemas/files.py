from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID  

class FileUploadResponse(BaseModel):
    file_id: UUID      
    original_name: str  # ✅ 이 줄을 꼭 추가해주세요!
    status: str

class UploadedFileResponse(BaseModel):
    id: UUID          
    session_id: UUID   
    user_email: str
    original_name: str
    storage_path: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True