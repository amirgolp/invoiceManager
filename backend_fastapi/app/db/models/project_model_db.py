from mongoengine import Document, StringField, ReferenceField, DateTimeField, UUIDField
from .user_model_db import User
from .workspace_model_db import Workspace # Assuming Workspace model is defined
import datetime
import uuid

class Project(Document):
    meta = {
        'collection': 'projects',
        'indexes': [
            'workspace', # Index on workspace for faster querying of projects within a workspace
            'created_by'
        ]
    }

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = StringField(required=True, max_length=255)
    description = StringField()
    emoji = StringField(default="📊") # Default emoji as in Pydantic model

    workspace = ReferenceField(Workspace, required=True, reverse_delete_rule=2) # Deny deletion of workspace if projects exist
                                                                                # Or use CASCADE (1) if projects should be deleted with workspace
                                                                                # Using DENY (2) for now, service layer must handle cleanup.
    created_by = ReferenceField(User, required=True)

    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        return super(Project, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def to_pydantic(self):
        from app.models.project_models import ProjectPublic # Local import
        return ProjectPublic(
            id=self.id,
            name=self.name,
            description=self.description,
            emoji=self.emoji,
            workspace_id=self.workspace.id, # Assuming workspace is always populated
            created_by_id=self.created_by.id, # Assuming created_by is always populated
            created_at=self.created_at,
            updated_at=self.updated_at
        )
