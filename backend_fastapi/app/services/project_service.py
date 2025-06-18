from typing import Optional, List
import uuid

from app.db.models.project_model_db import Project as ProjectDBModel
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.task_model_db import Task as TaskDBModel # Import TaskDBModel
from app.models.project_models import ProjectCreate, ProjectUpdate
from mongoengine.errors import ValidationError, DoesNotExist

class ProjectService:
    # ... (create, get_by_id, list_in_workspace, update methods as before) ...
    def create_project(self, user_db: UserDBModel, workspace_id: uuid.UUID, project_data: ProjectCreate) -> ProjectDBModel:
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).first()
            if not workspace: raise ValueError(f"Workspace with ID {workspace_id} not found.")
            new_project = ProjectDBModel(name=project_data.name, description=project_data.description, emoji=project_data.emoji, workspace=workspace, created_by=user_db)
            new_project.save()
            return new_project
        except ValidationError as e: raise ValueError(f"Project data validation error: {e}")
        except Exception as e: print(f"Unexpected error creating project: {e}"); raise ValueError(f"Could not create project: {e}")

    def get_project_by_id(self, project_id: uuid.UUID) -> Optional[ProjectDBModel]:
        try: return ProjectDBModel.objects(id=project_id).first()
        except Exception as e: print(f"Error fetching project {project_id}: {e}"); return None

    def list_projects_in_workspace(self, workspace_id: uuid.UUID) -> List[ProjectDBModel]:
        try:
            workspace = WorkspaceDBModel.objects(id=workspace_id).first()
            if not workspace: return []
            return list(ProjectDBModel.objects(workspace=workspace))
        except Exception as e: print(f"Error fetching projects for workspace {workspace_id}: {e}"); return []

    def update_project(self, project_id: uuid.UUID, workspace_id: uuid.UUID, data_update: ProjectUpdate, performing_user: UserDBModel) -> Optional[ProjectDBModel]:
        try:
            project = ProjectDBModel.objects(id=project_id, workspace=workspace_id).first()
            if not project: return None
            if data_update.name is not None: project.name = data_update.name
            if data_update.description is not None: project.description = data_update.description
            if data_update.emoji is not None: project.emoji = data_update.emoji
            project.save()
            return project
        except ValidationError as e: raise ValueError(f"Project update validation error: {e}")
        except Exception as e: print(f"Error updating project {project_id}: {e}"); raise ValueError(f"Could not update project: {e}")

    def delete_project(self, project_id: uuid.UUID, workspace_id: uuid.UUID, performing_user: UserDBModel) -> bool:
        try:
            project = ProjectDBModel.objects(id=project_id, workspace=workspace_id).first()
            if not project: return False

            # Cascade delete tasks associated with this project
            TaskDBModel.objects(project=project).delete()
            print(f"Deleted tasks for project {project_id}")

            project.delete()
            print(f"Deleted project {project_id} from workspace {workspace_id}")
            return True
        except Exception as e:
            print(f"Error deleting project {project_id} from workspace {workspace_id}: {e}")
            return False

project_service = ProjectService()
