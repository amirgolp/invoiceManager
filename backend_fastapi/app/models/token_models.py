from pydantic import BaseModel
from typing import Optional
from .user_models import UserPublic # For returning user info along with token

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None # Corresponds to 'sub' in JWT

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserPublic] = None # Optionally return user details on login/register
