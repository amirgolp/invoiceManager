from pydantic import BaseModel, Field, EmailStr # Added EmailStr
from typing import Optional
from datetime import datetime
import uuid
from .role_permission_models import RoleEnum
from .user_models import UserPublic # For richer member list response

class MemberBase(BaseModel): # Not directly used for request/response but good for structure
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: RoleEnum # Storing RoleEnum, but service uses role_name (string)

class MemberAdd(BaseModel): # For adding a new member
    user_email: EmailStr # Add member by their email
    role_name: str # Role name string, e.g., "MEMBER", "ADMIN"

class MemberUpdateRole(BaseModel): # For updating a member's role
    new_role_name: str

class MemberResponse(BaseModel): # Response model for a single member
    id: uuid.UUID
    user: UserPublic # Embed UserPublic details
    workspace_id: uuid.UUID
    role_name: str
    joined_at: datetime
    created_at: datetime # from MemberDBModel
    updated_at: datetime # from MemberDBModel

    class Config:
        from_attributes = True
