import time
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User  
from app.schemas.users import UserCreate, UserResponse  
from app.schemas.auth import Token  
from app.service.auth_service import auth_service
from app.api.deps import oauth2_scheme

router = APIRouter(prefix="/auth", tags=["auth"])

# 토큰 추출을 위한 OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/signup", response_model=UserResponse)
async def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    print(f"\n[{time.strftime('%H:%M:%S')}] [AUTH-API] Signup: {user_in.email}")

    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    hashed_pw = auth_service.hash_password(user_in.password)
    new_user = User(email=user_in.email, name=user_in.name, hashed_password=hashed_pw)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(user_in: UserCreate, db: Session = Depends(get_db)):
    print(f"\n[{time.strftime('%H:%M:%S')}] [AUTH-API] Login: {user_in.email}")

    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not auth_service.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다.")

    access_token = auth_service.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print(f"\n[{time.strftime('%H:%M:%S')}] [AUTH-CHECK] /me")

    email = auth_service.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")

    return {"email": user.email, "name": user.name, "status": "authenticated"}
