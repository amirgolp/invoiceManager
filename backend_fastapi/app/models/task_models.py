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

class TaskCreate(TaskBase):
    # project_id and workspace_id will be validated from path or request body
    # created_by_id will be set from the authenticated user
    # assigned_to_id is optional
    project_id: uuid.UUID
    workspace_id: uuid.UUID # Denormalized for easier queries, or could be derived from project
    assigned_to_id: Optional[uuid.UUID] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[uuid.UUID] = None

class TaskInDBBase(TaskBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_code: str = Field(default_factory=lambda: f"TASK-{str(uuid.uuid4())[:6].upper()}") # Example task code
    project_id: uuid.UUID
    workspace_id: uuid.UUID
    created_by_id: uuid.UUID
    assigned_to_id: Optional[uuid.UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True # For Pydantic v1
        # from_attributes = True # For Pydantic v2

class TaskPublic(TaskInDBBase):
    pass
