from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = "📊"

class ProjectCreate(ProjectBase):
    # workspace_id will be validated from path or request body
    # created_by_id will be set from the authenticated user
    workspace_id: uuid.UUID # Ensure this is provided during creation

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    emoji: Optional[str] = None

class ProjectInDBBase(ProjectBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workspace_id: uuid.UUID # Foreign Key to Workspace
    created_by_id: uuid.UUID # Foreign Key to User
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True # For Pydantic v1
        # from_attributes = True # For Pydantic v2

class ProjectPublic(ProjectInDBBase):
    pass
