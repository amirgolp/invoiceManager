from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum

class TaskStatusEnum(str, Enum):
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"

class TaskPriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatusEnum = TaskStatusEnum.TODO
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase): # project_id and workspace_id removed
    assigned_to_id: Optional[uuid.UUID] = None

class TaskUpdate(BaseModel): # Will be used for PUT requests later
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[uuid.UUID] = None # Allow re-assigning or un-assigning

class TaskInDBBase(TaskBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_code: str # Default factory handled by DB model
    project_id: uuid.UUID
    workspace_id: uuid.UUID
    created_by_id: uuid.UUID
    assigned_to_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskPublic(TaskInDBBase):
    pass
