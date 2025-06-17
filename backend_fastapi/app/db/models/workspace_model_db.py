from mongoengine import Document, StringField, ReferenceField, DateTimeField, UUIDField
from .user_model_db import User # Import User DB model
import datetime
import uuid

# Helper function to generate invite codes, can be moved to utils later
def generate_invite_code(length=8):
    return str(uuid.uuid4())[:length].upper()

class Workspace(Document):
    meta = {
        'collection': 'workspaces',
        'indexes': [
            'owner',
            {'fields': ['invite_code'], 'unique': True, 'sparse': True} # Invite code should be unique if present
        ]
    }
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = StringField(required=True, max_length=255)
    description = StringField()
    owner = ReferenceField(User, required=True)
    invite_code = StringField(unique=True, sparse=True, default=generate_invite_code) # Unique and auto-generated

    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow()
        if not self.invite_code: # Ensure invite_code is generated if not provided (e.g. for older docs if schema changes)
            self.invite_code = generate_invite_code()
        self.updated_at = datetime.datetime.utcnow()
        return super(Workspace, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def to_pydantic(self):
        from app.models.workspace_models import WorkspacePublic # Local import
        return WorkspacePublic(
            id=self.id,
            name=self.name,
            description=self.description,
            owner_id=self.owner.id, # Assuming owner is always populated
            invite_code=self.invite_code,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
