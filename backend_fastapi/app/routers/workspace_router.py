from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid

from app.services.workspace_service import workspace_service
from app.models.workspace_models import WorkspaceCreate, WorkspacePublic, WorkspaceUpdate
from app.db.models.user_model_db import User as UserDBModel
from app.routers.auth_router import get_current_active_user
from app.utils.rbac import RBACDepends, RBACResults
from app.models.role_permission_models import PermissionEnum

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

# ... (POST, GET single, GET list, PUT methods as before) ...
@router.post("", response_model=WorkspacePublic, status_code=status.HTTP_201_CREATED)
async def create_new_workspace(workspace_data: WorkspaceCreate, current_user: UserDBModel = Depends(get_current_active_user)):
    try:
        workspace_db = workspace_service.create_workspace(user_db=current_user, workspace_data=workspace_data)
        return workspace_db.to_pydantic()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in create_new_workspace endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while creating the workspace.")

@router.get("/{workspace_id}", response_model=WorkspacePublic)
async def read_workspace_by_id(workspace_id: uuid.UUID, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.VIEW_ONLY]))):
    workspace_db = workspace_service.get_workspace_by_id(workspace_id=workspace_id)
    if not workspace_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace_db.to_pydantic()

@router.get("", response_model=List[WorkspacePublic])
async def list_user_workspaces(current_user: UserDBModel = Depends(get_current_active_user)):
    workspaces_db_list = workspace_service.get_workspaces_for_user(user_db=current_user)
    return [ws.to_pydantic() for ws in workspaces_db_list]

@router.put("/{workspace_id}", response_model=WorkspacePublic)
async def update_existing_workspace(workspace_id: uuid.UUID, workspace_data: WorkspaceUpdate, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.EDIT_WORKSPACE]))):
    try:
        updated_workspace = workspace_service.update_workspace(workspace_id=workspace_id, data_update=workspace_data, performing_user=rbac_results.user)
        if not updated_workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or user cannot update")
        return updated_workspace.to_pydantic()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in update_existing_workspace endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while updating the workspace.")

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_workspace(
    workspace_id: uuid.UUID,
    rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.DELETE_WORKSPACE]))
):
    try:
        success = workspace_service.delete_workspace(workspace_id=workspace_id, performing_user=rbac_results.user)
        if not success:
            # Service returns False if workspace not found, or if other delete conditions fail
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or could not be deleted.")
        # No content to return on successful delete
    except ValueError as e: # Catch specific errors like permission denied from service if implemented
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in delete_existing_workspace endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while deleting the workspace.")
