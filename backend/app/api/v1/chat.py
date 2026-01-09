from fastapi import APIRouter, Depends, Form, File, UploadFile
from typing import List, Optional
from app.api.v1.auth import oauth2_scheme 
from app.service.auth_service import auth_service
from app.service.solar_service import solar_service
import time

router = APIRouter()

@router.post("")
async def chat_with_agent(
    message: str = Form(...),
    token: str = Depends(oauth2_scheme) 
):
    user_email = auth_service.verify_token(token)
    
    answer = await solar_service.get_chat_response(user_email, message)
    
    return {
        "user": user_email,
        "reply": answer,
        "timestamp": time.time()
    }