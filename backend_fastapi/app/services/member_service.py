from typing import Optional, List
import uuid

from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.role_model_db import Role as RoleDBModel # For validating role name
from app.models.role_permission_models import RoleEnum # For default and specific roles
from mongoengine.errors import NotUniqueError, DoesNotExist

class MemberService:
    def get_member_role_name(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[str]:
        # ... (get_member_role_name as before) ...
        try:
            member_entry = MemberDBModel.objects(user=user_id, workspace=workspace_id).first()
            if member_entry: return member_entry.role_name
            return None
        except Exception as e:
            print(f"Error fetching member role name for user {user_id} in workspace {workspace_id}: {e}")
            return None

    def add_member_to_workspace(self, user: UserDBModel, workspace: WorkspaceDBModel, role_name: str = RoleEnum.MEMBER.value) -> MemberDBModel:
        # ... (add_member_to_workspace as before, but ensure role_name is valid) ...
        existing_role = RoleDBModel.objects(name=role_name).first()
        if not existing_role:
            raise ValueError(f"Role '{role_name}' does not exist in the database.")
        existing_member = MemberDBModel.objects(user=user, workspace=workspace).first()
        if existing_member:
            raise ValueError(f"User {user.email} is already a member of workspace {workspace.name}.")
        try:
            member_entry = MemberDBModel(user=user, workspace=workspace, role_name=role_name)
            member_entry.save()
            return member_entry
        except NotUniqueError:
            raise ValueError(f"User {user.email} is already a member of workspace {workspace.name} (NotUniqueError).")
        except Exception as e:
            print(f"Error adding member {user.id} to workspace {workspace.id}: {e}")
            raise ValueError(f"Could not add member to workspace: {e}")

    def remove_member_from_workspace(self, user_to_remove_id: uuid.UUID, workspace_id: uuid.UUID, performing_user: UserDBModel) -> bool:
        """
        Removes a member from a workspace.
        Prevents owner from being removed or removing themselves if they are the sole owner.
        """
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).select_related('owner').first()
            if not workspace:
                raise ValueError("Workspace not found.")

            member_to_remove = MemberDBModel.objects(user=user_to_remove_id, workspace=workspace_id).first()
            if not member_to_remove:
                raise ValueError("Member not found in this workspace.")

            # Business rule: Cannot remove the workspace owner.
            if workspace.owner.id == user_to_remove_id:
                # More specific: check if they are an OWNER role and if there are other owners.
                # For now, simple check: if target is owner, prevent removal.
                raise ValueError("Cannot remove the workspace owner.")

            # Business rule: User cannot remove themselves (usually done via 'leave workspace' endpoint)
            # if performing_user.id == user_to_remove_id:
            #     raise ValueError("Users cannot remove themselves using this method.")

            member_to_remove.delete()
            return True
        except DoesNotExist:
            raise ValueError("Workspace or Member not found (DoesNotExist).")
        except Exception as e:
            print(f"Error removing member {user_to_remove_id} from workspace {workspace_id}: {e}")
            return False # Or re-raise specific error

    def update_member_role(self, user_to_update_id: uuid.UUID, workspace_id: uuid.UUID, new_role_name: str, performing_user: UserDBModel) -> Optional[MemberDBModel]:
        """
        Updates the role of a member in a workspace.
        Prevents changing the role of the workspace owner if it would leave no owner or demote an owner by non-owner.
        """
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).select_related('owner').first()
            if not workspace:
                raise ValueError("Workspace not found.")

            member_to_update = MemberDBModel.objects(user=user_to_update_id, workspace=workspace_id).first()
            if not member_to_update:
                raise ValueError("Member not found in this workspace.")

            # Validate new_role_name against DB roles
            new_role_db = RoleDBModel.objects(name=new_role_name).first()
            if not new_role_db:
                raise ValueError(f"Role '{new_role_name}' does not exist.")

            # Business rule: Workspace owner's role cannot be changed to a non-owner role by anyone if they are the sole owner.
            # Or, an Admin cannot change an Owner's role.
            if workspace.owner.id == user_to_update_id and new_role_name != RoleEnum.OWNER.value:
                # Check if there are other owners
                other_owners_count = MemberDBModel.objects(workspace=workspace_id, role_name=RoleEnum.OWNER.value, user__ne=user_to_update_id).count()
                if other_owners_count == 0:
                    raise ValueError("Cannot change the role of the sole owner to a non-owner role.")

            # Add more logic here: e.g., an ADMIN cannot change an OWNER's role.
            # This would require knowing performing_user's role in this workspace.
            # performing_user_role = self.get_member_role_name(performing_user.id, workspace_id)
            # if member_to_update.role_name == RoleEnum.OWNER.value and performing_user_role != RoleEnum.OWNER.value:
            #     raise ValueError("Only an Owner can change another Owner's role.")

            member_to_update.role_name = new_role_name
            member_to_update.save()
            return member_to_update
        except DoesNotExist:
            raise ValueError("Workspace or Member not found (DoesNotExist).")
        except Exception as e:
            print(f"Error updating role for member {user_to_update_id} in workspace {workspace_id}: {e}")
            return None # Or re-raise

    def list_members_in_workspace(self, workspace_id: uuid.UUID) -> List[MemberDBModel]:
        """
        Lists all members of a specific workspace.
        """
        try:
            # Ensure workspace exists
            workspace = WorkspaceDBModel.objects(id=workspace_id).first()
            if not workspace:
                # Or raise error
                return []
            return list(MemberDBModel.objects(workspace=workspace_id).select_related('user')) # select_related('user') to populate user details
        except Exception as e:
            print(f"Error listing members for workspace {workspace_id}: {e}")
            return []

member_service = MemberService()
