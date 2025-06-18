from mongoengine import Document, StringField, ReferenceField, DateTimeField, UUIDField, EnumField
from .user_model_db import User
from .project_model_db import Project
from .workspace_model_db import Workspace # For denormalized workspace_id
from app.models.task_models import TaskStatusEnum, TaskPriorityEnum # Pydantic Enums
import datetime
import uuid

# Helper function for task codes, can be moved to utils
def generate_task_code():
    return f"TASK-{str(uuid.uuid4())[:6].upper()}"

class Task(Document):
    meta = {
        'collection': 'tasks',
        'indexes': [
            'project',
            'workspace', # If denormalizing workspace ID
            'assigned_to',
            'status',
            'priority',
            'due_date'
        ]
    }

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    task_code = StringField(unique=True, default=generate_task_code)
    title = StringField(required=True, max_length=255)
    description = StringField()

    status = EnumField(TaskStatusEnum, default=TaskStatusEnum.TODO)
    priority = EnumField(TaskPriorityEnum, default=TaskPriorityEnum.MEDIUM)

    due_date = DateTimeField()

    project = ReferenceField(Project, required=True, reverse_delete_rule=1) # CASCADE delete if project is deleted
    workspace = ReferenceField(Workspace, required=True) # Denormalized for easier querying and RBAC context
                                                        # This is important: If Project's workspace is updated, this might get stale.
                                                        # Or, it could be derived from project.workspace at runtime.
                                                        # For now, explicit reference. reverse_delete_rule for workspace on task not set,
                                                        # as tasks should be deleted when project is deleted.

    created_by = ReferenceField(User, required=True)
    assigned_to = ReferenceField(User, null=True) # Task may not be assigned initially

    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

        # Ensure workspace is set from project if not directly provided
        if self.project and not self.workspace:
            self.workspace = self.project.workspace
        elif self.project and self.workspace and self.project.workspace != self.workspace:
            # This indicates an inconsistency, should ideally not happen if data is managed correctly
            # For now, let project's workspace be authoritative if there's a mismatch during save
            self.workspace = self.project.workspace
            print(f"Warning: Task {self.id} had inconsistent workspace. Set to project's workspace {self.project.workspace.id}")

        return super(Task, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_code}: {self.title}"

    def to_pydantic(self):
        from app.models.task_models import TaskPublic # Local import
        return TaskPublic(
            id=self.id,
            task_code=self.task_code,
            title=self.title,
            description=self.description,
            status=self.status,
            priority=self.priority,
            due_date=self.due_date,
            project_id=self.project.id,
            workspace_id=self.workspace.id, # Relies on workspace being correctly set
            created_by_id=self.created_by.id,
            assigned_to_id=self.assigned_to.id if self.assigned_to else None,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
