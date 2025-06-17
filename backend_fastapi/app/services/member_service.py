from typing import Optional
import uuid

from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.user_model_db import User as UserDBModel # For type hinting
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel # For type hinting
from app.models.role_permission_models import RoleEnum # For default role name
from mongoengine.errors import NotUniqueError # To catch duplicate member entries

class MemberService:
    def get_member_role_name(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[str]:
        try:
            member_entry = MemberDBModel.objects(user=user_id, workspace=workspace_id).first()
            if member_entry:
                return member_entry.role_name
            return None
        except Exception as e:
            print(f"Error fetching member role name for user {user_id} in workspace {workspace_id}: {e}")
            return None

    def add_member_to_workspace(self, user: UserDBModel, workspace: WorkspaceDBModel, role_name: str = RoleEnum.MEMBER.value) -> MemberDBModel:
        """
        Adds a user as a member to a workspace with a given role.
        Raises ValueError if member already exists or other issues.
        """
        # Check if user is already a member
        existing_member = MemberDBModel.objects(user=user, workspace=workspace).first()
        if existing_member:
            raise ValueError(f"User {user.email} is already a member of workspace {workspace.name}.")

        try:
            member_entry = MemberDBModel(
                user=user,
                workspace=workspace,
                role_name=role_name
            )
            member_entry.save() # This will use the unique_with constraint on (user, workspace)
            return member_entry
        except NotUniqueError: # Should be caught by the check above, but as a safeguard
            raise ValueError(f"User {user.email} is already a member of workspace {workspace.name} (NotUniqueError).")
        except Exception as e:
            # Log error e
            print(f"Error adding member {user.id} to workspace {workspace.id}: {e}")
            raise ValueError(f"Could not add member to workspace: {e}")


    # More methods like remove_member, update_member_role will be added later.

member_service = MemberService()
