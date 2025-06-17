from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class WorkspaceBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceUpdate(BaseModel): # New model for updates
    name: Optional[str] = None
    description: Optional[str] = None
    # owner_id is typically not changed, invite_code might have its own refresh mechanism

class WorkspaceInDBBase(WorkspaceBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    owner_id: uuid.UUID # Reference to User ID
    invite_code: str # Was: Field(default_factory=lambda: str(uuid.uuid4())[:8]) - default factory handled by DB model now
    created_at: datetime # Was: Field(default_factory=datetime.utcnow)
    updated_at: datetime # Was: Field(default_factory=datetime.utcnow)

    class Config:
        # orm_mode = True # For Pydantic v1, replaced by from_attributes in v2
        from_attributes = True # For Pydantic v2

class WorkspacePublic(WorkspaceInDBBase):
    pass
