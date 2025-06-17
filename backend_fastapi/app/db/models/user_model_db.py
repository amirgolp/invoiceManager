from mongoengine import Document, EmailField, StringField, BooleanField, DateTimeField, UUIDField, ReferenceField
import datetime
import uuid # For default UUID

# Forward reference for currentWorkspace if Workspace model is in another file or defined later
# class Workspace(Document): # Placeholder if defined in same file, otherwise just use "Workspace" as string
#     pass

class User(Document):
    meta = {
        'collection': 'users',
        'indexes': [
            'email',
            ('id', '+email') # example compound index
        ]
    }

    # Fields from Pydantic UserInDBBase / UserBase
    id = UUIDField(primary_key=True, default=uuid.uuid4) # Pydantic UserInDBBase has id: uuid.UUID
    email = EmailField(required=True, unique=True)
    name = StringField(max_length=255)
    profile_picture = StringField() # URL or path to picture
    is_active = BooleanField(default=True)
    last_login = DateTimeField()

    # current_workspace_id from Pydantic was Optional[str] or Optional[uuid.UUID]
    # In MongoEngine, this would be a ReferenceField if Workspace is another Document
    # For now, let's assume Workspace model will be created. Using 'Workspace' as a string for forward reference.
    current_workspace = ReferenceField('Workspace', required=False) # Or LazyReferenceField

    # Fields from Pydantic UserInDBBase
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow) # Should auto-update on save

    # Field from Pydantic UserInDB
    hashed_password = StringField(required=True)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        return super(User, self).save(*args, **kwargs)

    # To easily convert to Pydantic UserPublic model
    def to_pydantic(self):
        from app.models.user_models import UserPublic # Local import to avoid circular dependency issues

        user_data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "profile_picture": self.profile_picture,
            "is_active": self.is_active,
            "last_login": self.last_login,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_workspace_id": str(self.current_workspace.id) if self.current_workspace else None,
        }
        return UserPublic(**user_data)
