from mongoengine import Document, StringField, ListField, EnumField
from app.models.role_permission_models import PermissionEnum # My existing PermissionEnum

class Role(Document):
    meta = {
        'collection': 'roles',
        'indexes': [
            {'fields': ['name'], 'unique': True}
        ]
    }

    name = StringField(max_length=50, required=True, unique=True)
    # Storing permissions as a list of enum values.
    # Using the string value of the enum for storage is often robust.
    permissions = ListField(EnumField(PermissionEnum), default=[])

    def __str__(self):
        return self.name
