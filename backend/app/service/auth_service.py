import time
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# 1. 비밀번호 해싱 설정
# bcrypt 알고리즘을 사용하며, passlib와 bcrypt 최신 버전 간의 호환성을 위해 
# 이전 단계에서 설정한 대로 안전하게 관리합니다.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        # 서비스 초기화 시 설정 로드 확인
        # tqdm 대신 상세한 print 문을 사용하여 초기화 상태를 알립니다.
        print(f"[{time.strftime('%H:%M:%S')}] [AUTH-SERVICE] Initializing AuthService...")
        print(f"  - Algorithm: {settings.ALGORITHM}")
        print(f"  - Token Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")

    # --- 비밀번호 관련 로직 ---

    def hash_password(self, password: str) -> str:
        """
        사용자가 입력한 평문 비밀번호를 bcrypt로 해싱합니다.
        bcrypt의 72바이트 제한을 방지하기 위해 입력을 안전하게 처리합니다.
        """
        print(f"[{time.strftime('%H:%M:%S')}] [AUTH-SERVICE] Hashing new password...")
        return pwd_context.hash(password[:72])

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        평문 비밀번호와 DB에 저장된 해시값을 비교합니다.
        """
        print(f"[{time.strftime('%H:%M:%S')}] [AUTH-SERVICE] Verifying password match...")
        return pwd_context.verify(plain_password[:72], hashed_password)

    # --- JWT 토큰 관련 로직 ---

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        사용자 정보를 담은 JWT 액세스 토큰을 생성합니다.
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # 만료 시간(exp) 추가
        to_encode.update({"exp": expire})
        
        print(f"[{time.strftime('%H:%M:%S')}] [AUTH-SERVICE] Creating JWT for: {to_encode.get('sub')}")
        
        # config.py의 JWT_SECRET_KEY를 사용하여 인코딩
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        print(f"  - Token successfully generated.")
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[str]:
        """
        전달받은 JWT 토큰의 유효성을 검사하고 유저의 식별자(email)를 반환합니다.
        새로고침 시 /auth/me 엔드포인트에서 이 함수를 호출하여 세션을 유지합니다.
        """
        try:
            print(f"[{time.strftime('%H:%M:%S')}] [AUTH-SERVICE] Decoding incoming token...")
            
            # 토큰 복호화 시도
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            email: str = payload.get("sub")
            if email is None:
                print(f"  - Verification Failed: 'sub' claim missing in payload.")
                return None
            
            print(f"  - Verification Success: User {email} identified.")
            return email

        except JWTError as e:
            # 토큰 만료, 위변조 등 모든 JWT 관련 에러 처리
            print(f"  - Verification Failed: {str(e)}")
            return None

# 어디서든 동일한 설정을 사용할 수 있도록 인스턴스화하여 내보냅니다.
auth_service = AuthService()