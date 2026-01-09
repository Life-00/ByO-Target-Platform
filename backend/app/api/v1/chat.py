from fastapi import APIRouter, Form, File, UploadFile
from typing import List, Optional
from app.service.solar_service import SolarService
import time

router = APIRouter()
solar_service = SolarService()

@router.post("/chat")
async def chat_v1(
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    print(f"\n[{time.strftime('%H:%M:%S')}] [ROUTE] New Request Received")
    print(f"  - Message: {message[:30]}...")
    
    # 서비스 레이어 호출
    response = await solar_service.perform_analysis(message, files)
    
    return {"status": "success", "reply": response}