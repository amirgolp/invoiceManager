from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from datetime import datetime
import uuid

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    current_workspace_id: Optional[str] = None # Assuming ObjectId will be represented as str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: Optional[bool] = None
    current_workspace_id: Optional[str] = None

class UserInDBBase(UserBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True # Replaced from_attributes = True for Pydantic v1 compatibility if needed, else use from_attributes
        # For Pydantic v2, it's from_attributes = True

class UserPublic(UserInDBBase):
    pass # Excludes password by not inheriting it from UserCreate or defining it here

class UserInDB(UserInDBBase):
    hashed_password: str
