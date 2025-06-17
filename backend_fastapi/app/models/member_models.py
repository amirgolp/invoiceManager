from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
from .role_permission_models import RoleEnum # Import RoleEnum

class MemberBase(BaseModel):
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: RoleEnum = RoleEnum.MEMBER # Default role for new members

class MemberCreate(BaseModel): # Simplified for creation, user_id and workspace_id likely from path/context
    role: Optional[RoleEnum] = RoleEnum.MEMBER # Role can be specified on creation, defaults to MEMBER
    # user_id to add will likely be in request body or path
    user_email: Optional[str] = None # Often members are invited by email

class MemberUpdate(BaseModel):
    role: RoleEnum # Only role is updatable for a membership

class MemberInDBBase(MemberBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    joined_at: datetime = Field(default_factory=datetime.utcnow) # Tracks when membership started
    created_at: datetime = Field(default_factory=datetime.utcnow) # Record creation time
    updated_at: datetime = Field(default_factory=datetime.utcnow) # Record update time

    class Config:
        orm_mode = True # For Pydantic v1
        # from_attributes = True # For Pydantic v2

class MemberPublic(MemberInDBBase):
    # Potentially join with User model to provide more user details
    # For now, it will return IDs and role.
    pass

# This model might be useful for responses that include more details
class MemberDetailsPublic(MemberPublic):
    user_name: Optional[str] = None # Example: to be populated from User model
    user_email: Optional[str] = None # Example: to be populated from User model
