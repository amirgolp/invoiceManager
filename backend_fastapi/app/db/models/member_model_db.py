from mongoengine import Document, ReferenceField, StringField, DateTimeField, UUIDField
from .user_model_db import User  # Import User DB model
# Workspace model will also be a DB model, forward reference for now as 'Workspace'
# from .workspace_model_db import Workspace # This will be created soon
from app.models.role_permission_models import RoleEnum # For default role value, store as string
import datetime
import uuid

class Member(Document):
    meta = {
        'collection': 'members',
        'indexes': [
            {'fields': ('user', 'workspace'), 'unique': True}, # A user can only be a member of a workspace once
            'user',
            'workspace'
        ]
    }

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    user = ReferenceField(User, required=True)
    workspace = ReferenceField('Workspace', required=True) # Forward reference to Workspace DB model

    # Store role name as string, matching the 'name' field in the RoleDBModel
    # This allows flexibility if roles are fully DB driven.
    # Defaulting to RoleEnum.MEMBER.value for new members.
    role_name = StringField(required=True, default=RoleEnum.MEMBER.value)

    joined_at = DateTimeField(default=datetime.datetime.utcnow)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        return super(Member, self).save(*args, **kwargs)

    def __str__(self):
        return f"Member(user={self.user.id}, workspace={self.workspace.id}, role='{self.role_name}')"
