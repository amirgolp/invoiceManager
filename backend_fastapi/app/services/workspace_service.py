from typing import Optional, List
import uuid

from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.project_model_db import Project as ProjectDBModel # Import ProjectDBModel
from app.models.workspace_models import WorkspaceCreate, WorkspaceUpdate
from app.services.member_service import member_service
from app.models.role_permission_models import RoleEnum
from mongoengine.errors import NotUniqueError, ValidationError

class WorkspaceService:
    # ... (create, get_by_id, get_for_user, update methods as before) ...
    def create_workspace(self, user_db: UserDBModel, workspace_data: WorkspaceCreate) -> WorkspaceDBModel:
        try:
            new_workspace = WorkspaceDBModel(name=workspace_data.name, description=workspace_data.description, owner=user_db)
            new_workspace.save()
            try:
                member_service.add_member_to_workspace(user=user_db, workspace=new_workspace, role_name=RoleEnum.OWNER.value)
            except ValueError as e:
                new_workspace.delete()
                raise ValueError(f"Workspace creation failed: could not add owner as member: {e}")
            return new_workspace
        except NotUniqueError: raise ValueError("Workspace with this name or invite code might already exist.")
        except ValidationError as e: raise ValueError(f"Workspace data validation error: {e}")
        except Exception as e: print(f"Unexpected error creating workspace for user {user_db.id}: {e}"); raise ValueError(f"Could not create workspace: {e}")

    def get_workspace_by_id(self, workspace_id: uuid.UUID) -> Optional[WorkspaceDBModel]:
        try: return WorkspaceDBModel.objects(id=workspace_id).first()
        except Exception as e: print(f"Error fetching workspace {workspace_id}: {e}"); return None

    def get_workspaces_for_user(self, user_db: UserDBModel) -> List[WorkspaceDBModel]:
        from app.db.models.member_model_db import Member as MemberDBModel
        try:
            member_entries = MemberDBModel.objects(user=user_db).select_related('workspace')
            workspaces = [member.workspace for member in member_entries if member.workspace is not None]
            return workspaces
        except Exception as e: print(f"Error fetching workspaces for user {user_db.id}: {e}"); return []

    def update_workspace(self, workspace_id: uuid.UUID, data_update: WorkspaceUpdate, performing_user: UserDBModel) -> Optional[WorkspaceDBModel]:
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).first()
            if not workspace: return None
            if data_update.name is not None: workspace.name = data_update.name
            if data_update.description is not None: workspace.description = data_update.description
            workspace.save()
            return workspace
        except ValidationError as e: raise ValueError(f"Workspace update validation error: {e}")
        except Exception as e: print(f"Error updating workspace {workspace_id}: {e}"); raise ValueError(f"Could not update workspace: {e}")

    def delete_workspace(self, workspace_id: uuid.UUID, performing_user: UserDBModel) -> bool:
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).first()
            if not workspace: return False

            # Cascade delete: Projects (and their tasks indirectly via Project's delete rule or explicit task deletion)
            # First, delete tasks within projects of this workspace (if Task model had direct workspace link or via project)
            # Then, delete projects
            projects_in_workspace = ProjectDBModel.objects(workspace=workspace)
            for project in projects_in_workspace:
                # TODO: Call project_service.delete_project(project.id, workspace.id, performing_user) if it handles task cleanup
                # Or, if Project model has task cascade delete rule, just deleting project is enough.
                # For now, direct delete of projects. Task cleanup is TODO in ProjectService.delete_project.
                # TaskDBModel.objects(project=project).delete() # If tasks need explicit deletion here
                project.delete() # This will fail if Project's reverse_delete_rule for tasks is DENY and tasks exist.
            print(f"Deleted projects for workspace {workspace_id}")

            MemberDBModel.objects(workspace=workspace).delete()
            print(f"Deleted members for workspace {workspace_id}")

            workspace.delete()
            print(f"Deleted workspace {workspace_id}")
            return True
        except Exception as e:
            print(f"Error deleting workspace {workspace_id}: {e}")
            return False

workspace_service = WorkspaceService()
