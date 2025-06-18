from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = "📊"

class ProjectCreate(ProjectBase): # workspace_id is removed, as it's taken from path param
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    emoji: Optional[str] = None

class ProjectInDBBase(ProjectBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workspace_id: uuid.UUID # Foreign Key to Workspace
    created_by_id: uuid.UUID # Foreign Key to User
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectPublic(ProjectInDBBase):
    pass
