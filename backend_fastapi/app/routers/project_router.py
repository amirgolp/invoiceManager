from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid

from app.services.project_service import project_service
from app.models.project_models import ProjectCreate, ProjectPublic, ProjectUpdate
from app.db.models.user_model_db import User as UserDBModel
from app.routers.auth_router import get_current_active_user
from app.utils.rbac import RBACDepends, RBACResults
from app.models.role_permission_models import PermissionEnum

router = APIRouter(tags=["Projects"])

# ... (POST, GET single, GET list, PUT methods as before) ...
@router.post("/workspaces/{workspace_id}/projects", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
async def create_new_project_in_workspace(workspace_id: uuid.UUID, project_data: ProjectCreate, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.CREATE_PROJECT]))):
    current_user = rbac_results.user
    try:
        project_db = project_service.create_project(user_db=current_user, workspace_id=workspace_id, project_data=project_data)
        return project_db.to_pydantic()
    except ValueError as e:
        if "Workspace with ID" in str(e) and "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in create_new_project_in_workspace endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/workspaces/{workspace_id}/projects/{project_id}", response_model=ProjectPublic)
async def read_project_by_id_in_workspace(workspace_id: uuid.UUID, project_id: uuid.UUID, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.VIEW_ONLY]))):
    project_db = project_service.get_project_by_id(project_id=project_id)
    if not project_db or project_db.workspace.id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in this workspace.")
    return project_db.to_pydantic()

@router.get("/workspaces/{workspace_id}/projects", response_model=List[ProjectPublic])
async def list_all_projects_in_workspace(workspace_id: uuid.UUID, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.VIEW_ONLY]))):
    projects_db_list = project_service.list_projects_in_workspace(workspace_id=workspace_id)
    return [p.to_pydantic() for p in projects_db_list]

@router.put("/workspaces/{workspace_id}/projects/{project_id}", response_model=ProjectPublic)
async def update_existing_project(workspace_id: uuid.UUID, project_id: uuid.UUID, project_data: ProjectUpdate, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.EDIT_PROJECT]))):
    try:
        updated_project_db = project_service.update_project(project_id=project_id, workspace_id=workspace_id, data_update=project_data, performing_user=rbac_results.user)
        if not updated_project_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in this workspace or update failed.")
        return updated_project_db.to_pydantic()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in update_existing_project endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while updating the project.")

@router.delete("/workspaces/{workspace_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.DELETE_PROJECT]))
):
    try:
        success = project_service.delete_project(
            project_id=project_id,
            workspace_id=workspace_id,
            performing_user=rbac_results.user
        )
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in this workspace or could not be deleted.")
        # No content to return on successful delete
    except ValueError as e: # Catch specific errors like permission denied from service if implemented
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in delete_existing_project endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while deleting the project.")
