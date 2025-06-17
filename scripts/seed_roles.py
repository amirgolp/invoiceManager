import sys
import os
from mongoengine import connect, disconnect

# Adjust path to import from app
# This assumes the script is run from the 'backend_fastapi' directory or that the path is adjusted.
# For simplicity, let's add the project root to sys.path if running directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.models.role_model_db import Role as RoleDBModel
from app.models.role_permission_models import PermissionEnum, RoleEnum # Using RoleEnum for keys initially
from app.config.settings import settings # For DB URI

# Define the roles and their permissions, similar to the old role-permission.ts
# Using RoleEnum as keys for clarity here, will use their string values for DB.
SEED_ROLE_PERMISSIONS = {
    RoleEnum.OWNER: [
        PermissionEnum.CREATE_WORKSPACE, PermissionEnum.EDIT_WORKSPACE, PermissionEnum.DELETE_WORKSPACE, PermissionEnum.MANAGE_WORKSPACE_SETTINGS,
        PermissionEnum.ADD_MEMBER, PermissionEnum.CHANGE_MEMBER_ROLE, PermissionEnum.REMOVE_MEMBER,
        PermissionEnum.CREATE_PROJECT, PermissionEnum.EDIT_PROJECT, PermissionEnum.DELETE_PROJECT,
        PermissionEnum.CREATE_TASK, PermissionEnum.EDIT_TASK, PermissionEnum.DELETE_TASK,
        PermissionEnum.VIEW_ONLY,
    ],
    RoleEnum.ADMIN: [
        PermissionEnum.ADD_MEMBER, PermissionEnum.CREATE_PROJECT, PermissionEnum.EDIT_PROJECT, PermissionEnum.DELETE_PROJECT,
        PermissionEnum.CREATE_TASK, PermissionEnum.EDIT_TASK, PermissionEnum.DELETE_TASK,
        PermissionEnum.MANAGE_WORKSPACE_SETTINGS, PermissionEnum.EDIT_WORKSPACE, # Added EDIT_WORKSPACE for admin
        PermissionEnum.VIEW_ONLY,
    ],
    RoleEnum.MEMBER: [
        PermissionEnum.VIEW_ONLY, PermissionEnum.CREATE_TASK, PermissionEnum.EDIT_TASK,
    ]
}

def seed_database():
    print("Connecting to database for seeding...")
    try:
        connect(host=settings.MONGODB_URI)
        print(f"Connected to MongoDB: {settings.MONGODB_URI}")

        print("Clearing existing roles...")
        RoleDBModel.objects.delete() # Clears all roles

        print("Seeding new roles...")
        for role_enum_key, permissions_list in SEED_ROLE_PERMISSIONS.items():
            role_name = role_enum_key.value # Get string value like "OWNER"

            # Ensure all permissions are valid PermissionEnum members
            valid_permissions = [p for p in permissions_list if isinstance(p, PermissionEnum)]

            role_doc = RoleDBModel(
                name=role_name,
                permissions=valid_permissions
            )
            role_doc.save()
            print(f"Role '{role_name}' seeded with {len(valid_permissions)} permissions.")

        print("Database seeding completed successfully.")

    except Exception as e:
        print(f"Error during database seeding: {e}")
    finally:
        print("Disconnecting from database...")
        disconnect()

if __name__ == "__main__":
    print("Starting database seeder script...")
    # This setup allows running the script directly: python scripts/seed_roles.py
    # Ensure environment variables (like MONGODB_URI from .env) are loaded if settings rely on them.
    # For .env loading, python-dotenv can be used if the script is run standalone.
    # However, settings.py already handles .env loading via pydantic-settings.
    seed_database()
