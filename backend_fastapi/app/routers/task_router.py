from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid

from app.services.task_service import task_service
from app.models.task_models import TaskCreate, TaskPublic, TaskUpdate
from app.db.models.user_model_db import User as UserDBModel
from app.routers.auth_router import get_current_active_user
from app.utils.rbac import RBACDepends, RBACResults
from app.models.role_permission_models import PermissionEnum

router = APIRouter(tags=["Tasks"])

# ... (POST, GET single, GET list, PUT methods as before) ...
@router.post("/workspaces/{workspace_id}/projects/{project_id}/tasks", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
async def create_new_task_in_project(workspace_id: uuid.UUID, project_id: uuid.UUID, task_data: TaskCreate, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.CREATE_TASK]))):
    current_user = rbac_results.user
    try:
        task_db = task_service.create_task(user_db=current_user, project_id=project_id, task_data=task_data)
        return task_db.to_pydantic()
    except ValueError as e:
        if "Project with ID" in str(e) and "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in create_new_task_in_project endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}", response_model=TaskPublic)
async def read_task_by_id_in_project(workspace_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.VIEW_ONLY]))):
    task_db = task_service.get_task_by_id(task_id=task_id)
    if not task_db or task_db.project.id != project_id or task_db.workspace.id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project/workspace.")
    return task_db.to_pydantic()

@router.get("/workspaces/{workspace_id}/projects/{project_id}/tasks", response_model=List[TaskPublic])
async def list_all_tasks_in_project(workspace_id: uuid.UUID, project_id: uuid.UUID, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.VIEW_ONLY]))):
    tasks_db_list = task_service.list_tasks_in_project(project_id=project_id)
    return [t.to_pydantic() for t in tasks_db_list if t.workspace.id == workspace_id]

@router.put("/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}", response_model=TaskPublic)
async def update_existing_task(workspace_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID, task_data: TaskUpdate, rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.EDIT_TASK]))):
    try:
        updated_task_db = task_service.update_task(task_id=task_id, project_id=project_id, workspace_id=workspace_id, data_update=task_data, performing_user=rbac_results.user)
        if not updated_task_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project/workspace or update failed.")
        return updated_task_db.to_pydantic()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in update_existing_task endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while updating the task.")

@router.delete("/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_task(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.DELETE_TASK]))
):
    try:
        success = task_service.delete_task(
            task_id=task_id,
            project_id=project_id,
            workspace_id=workspace_id,
            performing_user=rbac_results.user
        )
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project/workspace or could not be deleted.")
        # No content to return on successful delete
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in delete_existing_task endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while deleting the task.")
