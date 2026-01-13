from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FileUploadResponse(BaseModel):
    file_id: str
    original_name: str
    status: str

class UploadedFileResponse(BaseModel):
    id: str
    session_id: str
    user_email: str
    original_name: str
    storage_path: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
