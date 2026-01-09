from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import UserCreate, UserResponse, Token
from app.service.auth_service import auth_service
import time

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

fake_users_db = {}

@router.post("/signup", response_model=UserResponse)
async def signup(user_in: UserCreate):
    print(f"\n[{time.strftime('%H:%M:%S')}] [API] Signup Request: {user_in.email}")
    
    if user_in.email in fake_users_db:
        print(f"  - Error: User {user_in.email} already exists.")
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    
    hashed_pw = auth_service.hash_password(user_in.password)
    new_user = {
        "id": len(fake_users_db) + 1,
        "email": user_in.email,
        "name": user_in.name,
        "hashed_password": hashed_pw
    }
    fake_users_db[user_in.email] = new_user
    
    print(f"  - Success: User {user_in.email} registered. (Hashed PW: {hashed_pw[:10]}...)")
    return new_user

@router.post("/login", response_model=Token)
async def login(user_in: UserCreate): # OAuth2PasswordRequestForm 대신 간단하게 구현
    print(f"\n[{time.strftime('%H:%M:%S')}] [API] Login Attempt: {user_in.email}")
    
    user = fake_users_db.get(user_in.email)
    if not user or not auth_service.verify_password(user_in.password, user["hashed_password"]):
        print(f"  - Failure: Invalid credentials for {user_in.email}")
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다.")
    
    access_token = auth_service.create_access_token(data={"sub": user["email"]})
    print(f"  - Success: {user_in.email} logged in.")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_my_info(token: str = Depends(oauth2_scheme)):
    """
    프론트엔드 새로고침 시 토큰의 유효성을 검사하는 API
    """
    print(f"\n[{time.strftime('%H:%M:%S')}] [AUTH-CHECK] Verifying session token...")
    
    email = auth_service.verify_token(token)
    
    if not email:
        print(f"  - Result: Token is invalid or expired.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="세션이 만료되었습니다. 다시 로그인해주세요.",
        )
    
    print(f"  - Result: Token verified for user: {email}")
    return {"email": email, "status": "authenticated"}