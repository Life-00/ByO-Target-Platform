from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.service.auth_service import auth_service
from app.models.user import User  # SQLAlchemy User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    email = auth_service.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")
    return email

def get_current_user(email: str = Depends(get_current_user_email), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    return user
