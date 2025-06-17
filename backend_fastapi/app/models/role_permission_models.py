from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

class RoleEnum(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"

class PermissionEnum(str, Enum):
    # Workspace Permissions
    CREATE_WORKSPACE = "CREATE_WORKSPACE"
    DELETE_WORKSPACE = "DELETE_WORKSPACE"
    EDIT_WORKSPACE = "EDIT_WORKSPACE"
    MANAGE_WORKSPACE_SETTINGS = "MANAGE_WORKSPACE_SETTINGS"

    # Member Permissions
    ADD_MEMBER = "ADD_MEMBER"
    CHANGE_MEMBER_ROLE = "CHANGE_MEMBER_ROLE"
    REMOVE_MEMBER = "REMOVE_MEMBER"

    # Project Permissions
    CREATE_PROJECT = "CREATE_PROJECT"
    EDIT_PROJECT = "EDIT_PROJECT"
    DELETE_PROJECT = "DELETE_PROJECT"

    # Task Permissions
    CREATE_TASK = "CREATE_TASK"
    EDIT_TASK = "EDIT_TASK"
    DELETE_TASK = "DELETE_TASK"

    # General View Permission
    VIEW_ONLY = "VIEW_ONLY"

# Basic Role model if we need to store roles with specific permissions
class RoleBase(BaseModel):
    name: RoleEnum
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permissions: List[PermissionEnum] = []

class RoleInDBBase(RoleBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    permissions: List[PermissionEnum] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True # For Pydantic v1
        # from_attributes = True # For Pydantic v2

class RolePublic(RoleInDBBase):
    pass
