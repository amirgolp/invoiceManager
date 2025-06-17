from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any
from jose import jwt, JWTError
from app.config.settings import settings
from app.db.redis_db import store_token_jti # Import Redis utility
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    jti = str(uuid.uuid4()) # Unique token identifier
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        expires_in_seconds = int(expires_delta.total_seconds())
    else:
        delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.now(timezone.utc) + delta
        expires_in_seconds = int(delta.total_seconds())

    to_encode = {"exp": expire, "sub": str(subject), "jti": jti}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # Store JTI in Redis
    store_token_jti(jti=jti, user_id=str(subject), expires_in_seconds=expires_in_seconds)

    return encoded_jwt
