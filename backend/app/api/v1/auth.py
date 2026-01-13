import time
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user_db import User  
from app.models.user import UserCreate, UserResponse, Token  
from app.service.auth_service import auth_service

router = APIRouter()

# 토큰 추출을 위한 OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

@router.post("/signup", response_model=UserResponse)
async def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    print(f"\n[{time.strftime('%H:%M:%S')}] [AUTH-API] Signup attempt for: {user_in.email}")
    
    # 1. 중복 유저 체크 (ORM 사용)
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        print(f"  - Error: User {user_in.email} already exists in DB.")
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    
    # 2. 새로운 유저 객체 생성
    hashed_pw = auth_service.hash_password(user_in.password)
    new_user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=hashed_pw
    )
    
    # 3. DB 저장
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"  - Success: User registered with ID {new_user.id}")
    return new_user

@router.post("/login", response_model=Token)
async def login(user_in: UserCreate, db: Session = Depends(get_db)):
    print(f"\n[{time.strftime('%H:%M:%S')}] [AUTH-API] Login attempt: {user_in.email}")
    
    # 1. 유저 조회
    user = db.query(User).filter(User.email == user_in.email).first()
    
    # 2. 검증
    if not user or not auth_service.verify_password(user_in.password, user.hashed_password):
        print(f"  - Failure: Invalid credentials for {user_in.email}")
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다.")
    
    # 3. 토큰 발급
    access_token = auth_service.create_access_token(data={"sub": user.email})
    print(f"  - Success: JWT issued for {user.email}")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_my_info(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    프론트엔드 새로고침 시 토큰 유효성 검사 및 유저 정보 반환
    """
    print(f"\n[{time.strftime('%H:%M:%S')}] [AUTH-CHECK] Verifying session via token...")
    
    email = auth_service.verify_token(token)
    if not email:
        print(f"  - Result: Token invalid.")
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")
    
    # 유효한 경우 DB에서 최신 정보 조회
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")

    print(f"  - Result: Welcome back, {user.name}")
    return {"email": user.email, "name": user.name, "status": "authenticated"}