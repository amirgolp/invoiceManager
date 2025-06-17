from typing import Optional, List
import uuid

from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.member_model_db import Member as MemberDBModel # Import MemberDBModel
from app.models.workspace_models import WorkspaceCreate, WorkspaceUpdate
from app.services.member_service import member_service
from app.models.role_permission_models import RoleEnum
from mongoengine.errors import NotUniqueError, ValidationError

class WorkspaceService:
    def create_workspace(self, user_db: UserDBModel, workspace_data: WorkspaceCreate) -> WorkspaceDBModel:
        # ... (create_workspace method as before) ...
        try:
            new_workspace = WorkspaceDBModel(
                name=workspace_data.name,
                description=workspace_data.description,
                owner=user_db
            )
            new_workspace.save()
            try:
                member_service.add_member_to_workspace(
                    user=user_db,
                    workspace=new_workspace,
                    role_name=RoleEnum.OWNER.value
                )
            except ValueError as e:
                print(f"Error adding owner as member during workspace creation: {e}. Workspace {new_workspace.id} created but owner not added as member.")
                # Consider deleting new_workspace if owner cannot be added
                new_workspace.delete() # Rollback workspace creation
                raise ValueError(f"Workspace creation failed: could not add owner as member: {e}")
            return new_workspace
        except NotUniqueError:
            raise ValueError("Workspace with this name or invite code might already exist.")
        except ValidationError as e:
            raise ValueError(f"Workspace data validation error: {e}")
        except Exception as e:
            print(f"Unexpected error creating workspace for user {user_db.id}: {e}")
            raise ValueError(f"Could not create workspace: {e}")

    def get_workspace_by_id(self, workspace_id: uuid.UUID) -> Optional[WorkspaceDBModel]:
        # ... (get_workspace_by_id method as before) ...
        try:
            return WorkspaceDBModel.objects(id=workspace_id).first()
        except Exception as e:
            print(f"Error fetching workspace {workspace_id}: {e}")
            return None

    def get_workspaces_for_user(self, user_db: UserDBModel) -> List[WorkspaceDBModel]:
        # ... (get_workspaces_for_user method as before) ...
        from app.db.models.member_model_db import Member as MemberDBModel # Keep local import if preferred
        try:
            member_entries = MemberDBModel.objects(user=user_db).select_related('workspace') # Ensure workspace is fetched
            workspaces = [member.workspace for member in member_entries if member.workspace is not None]
            # Filter out None workspaces that might result from stale member entries if workspaces were deleted without cleaning members
            return workspaces
        except Exception as e:
            print(f"Error fetching workspaces for user {user_db.id}: {e}")
            return []

    def update_workspace(self, workspace_id: uuid.UUID, data_update: WorkspaceUpdate, performing_user: UserDBModel) -> Optional[WorkspaceDBModel]:
        # ... (update_workspace method as before) ...
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).first()
            if not workspace:
                return None
            if data_update.name is not None:
                workspace.name = data_update.name
            if data_update.description is not None:
                workspace.description = data_update.description
            workspace.save()
            return workspace
        except ValidationError as e:
            raise ValueError(f"Workspace update validation error: {e}")
        except Exception as e:
            print(f"Error updating workspace {workspace_id}: {e}")
            raise ValueError(f"Could not update workspace: {e}")

    def delete_workspace(self, workspace_id: uuid.UUID, performing_user: UserDBModel) -> bool:
        """
        Deletes a workspace and its associated member entries.
        Authorization (e.g., user is owner) is handled by RBAC in the router.
        TODO: Implement cascade delete for Projects and Tasks within this workspace.
        """
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).first()
            if not workspace:
                return False # Or raise NotFoundError

            # Add additional checks here if needed, e.g. only owner can delete
            # if workspace.owner.id != performing_user.id:
            #     raise ValueError("Only the workspace owner can delete the workspace.")

            # Delete associated member entries
            MemberDBModel.objects(workspace=workspace).delete()
            print(f"Deleted members for workspace {workspace_id}")

            # TODO: Delete associated projects and their tasks here
            # ProjectDBModel.objects(workspace=workspace).delete() (and tasks within those projects)

            workspace.delete()
            print(f"Deleted workspace {workspace_id}")
            return True
        except Exception as e:
            print(f"Error deleting workspace {workspace_id}: {e}")
            # Consider raising a more specific error or returning False based on policy
            # For now, let it be caught by router's generic error handler if it's unexpected.
            return False

workspace_service = WorkspaceService()
