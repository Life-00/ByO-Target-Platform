"""
Security utilities for password hashing and JWT token management.

This module provides:
- Password hashing and verification (bcrypt)
- JWT token generation and verification
- Token payload creation
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import settings

# Password hashing context with truncate_error to handle long passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", truncate_error=True)


# ============================================================================
# Password Management
# ============================================================================


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.
    
    Bcrypt has a 72-byte limit, so passwords longer than 72 bytes are truncated.
    This is handled automatically to prevent errors with long passwords.
    
    Args:
        password: Plaintext password to hash (will be truncated to 72 bytes if longer)
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
    """
    # Truncate password to 72 bytes (bcrypt limit)
    # UTF-8 encoding: each character is 1-4 bytes
    password_bytes = password.encode('utf-8')[:72]
    truncated_password = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.hash(truncated_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password.
    
    Bcrypt has a 72-byte limit, so passwords longer than 72 bytes are truncated
    to match the hashing behavior.
    
    Args:
        plain_password: Plaintext password to verify (will be truncated to 72 bytes if longer)
        hashed_password: Hashed password to compare against
        
    Returns:
        True if passwords match, False otherwise
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    # Truncate password to 72 bytes to match hashing behavior
    password_bytes = plain_password.encode('utf-8')[:72]
    truncated_password = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.verify(truncated_password, hashed_password)


# ============================================================================
# JWT Token Management
# ============================================================================


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None,
) -> str:
    """Create a JWT access token.
    
    Args:
        subject: Subject claim (typically user ID)
        expires_delta: Optional custom expiration time
        additional_claims: Optional additional claims to include
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token = create_access_token(subject="user123")
        >>> payload = decode_token(token)
        >>> payload["sub"]
        'user123'
    """
    if expires_delta:
        expire = datetime.now(settings.timezone) + expires_delta
    else:
        expire = datetime.now(settings.timezone) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(settings.timezone),
    }
    
    # Add additional claims
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    
    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token with longer expiration.
    
    Args:
        subject: Subject claim (typically user ID)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.now(settings.timezone) + expires_delta
    else:
        expire = datetime.now(settings.timezone) + timedelta(
            days=settings.refresh_token_expire_days
        )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(settings.timezone),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Token payload dict if valid, None if invalid or expired
        
    Example:
        >>> token = create_access_token("user123")
        >>> payload = decode_token(token)
        >>> payload["sub"]
        'user123'
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> Optional[str]:
    """Verify a token and extract the subject.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Subject (user ID) if token is valid, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    subject: str = payload.get("sub")
    if subject is None:
        return None
    
    return subject


def get_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """Extract JWT token from Authorization header.
    
    Expected format: "Bearer <token>"
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        Token string if valid format, None otherwise
        
    Example:
        >>> token = get_token_from_header("Bearer eyJhbGc...")
        >>> token
        'eyJhbGc...'
    """
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


# ============================================================================
# Token Validation Helpers
# ============================================================================


def is_token_expired(token: str) -> bool:
    """Check if a token is expired.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token is expired, False if valid or invalid
    """
    payload = decode_token(token)
    if payload is None:
        return True
    
    exp = payload.get("exp")
    if exp is None:
        return True
    
    return datetime.fromtimestamp(exp, tz=settings.timezone) < datetime.now(settings.timezone)


def get_token_info(token: str) -> Optional[dict]:
    """Get detailed information about a token.
    
    Args:
        token: JWT token to inspect
        
    Returns:
        Dict with token info {
            "subject": user_id,
            "expires_at": datetime,
            "issued_at": datetime,
            "is_expired": bool,
            "type": "access" or "refresh"
        } or None if invalid
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    exp_ts = payload.get("exp")
    iat_ts = payload.get("iat")
    
    return {
        "subject": payload.get("sub"),
        "expires_at": datetime.fromtimestamp(exp_ts, tz=settings.timezone) if exp_ts else None,
        "issued_at": datetime.fromtimestamp(iat_ts, tz=settings.timezone) if iat_ts else None,
        "is_expired": is_token_expired(token),
        "type": payload.get("type", "access"),
    }
