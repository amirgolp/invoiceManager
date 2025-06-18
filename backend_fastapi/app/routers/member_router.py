from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid

from app.services.member_service import member_service
from app.services.auth_service import auth_service # For fetching user by email
from app.models.member_models import MemberAdd, MemberUpdateRole, MemberResponse
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel # For workspace validation
from app.db.models.member_model_db import Member as MemberDBModel # For converting to Pydantic
from app.routers.auth_router import get_current_active_user
from app.utils.rbac import RBACDepends, RBACResults
from app.models.role_permission_models import PermissionEnum

router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["Workspace Members"])

def convert_member_db_to_response(member_db: MemberDBModel) -> MemberResponse:
    # UserDBModel's to_pydantic() returns UserPublic which is what MemberResponse.user expects
    user_public = member_db.user.to_pydantic() if member_db.user else None
    if not user_public: # Should not happen if member.user is a required ReferenceField and populated
        raise ValueError("Member has no associated user details.")

    return MemberResponse(
        id=member_db.id,
        user=user_public,
        workspace_id=member_db.workspace.id, # Assumes workspace is populated or just ID is fine
        role_name=member_db.role_name,
        joined_at=member_db.joined_at,
        created_at=member_db.created_at,
        updated_at=member_db.updated_at
    )

@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    member_add_data: MemberAdd,
    rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.ADD_MEMBER]))
):
    performing_user = rbac_results.user # User performing the action

    # Find the workspace
    workspace = WorkspaceDBModel.objects(id=workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    # Find the user to be added by email
    user_to_add = auth_service.get_user_by_email(email=member_add_data.user_email)
    if not user_to_add:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with email {member_add_data.user_email} not found.")

    try:
        member_db = member_service.add_member_to_workspace(
            user=user_to_add,
            workspace=workspace,
            role_name=member_add_data.role_name
        )
        # member_db.user should be populated by virtue of passing UserDBModel to service
        # member_db.workspace also
        return convert_member_db_to_response(member_db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in add_workspace_member: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not add member.")


@router.get("", response_model=List[MemberResponse])
async def list_workspace_members(
    workspace_id: uuid.UUID,
    rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.VIEW_ONLY])) # Or a specific view members perm
):
    members_db_list = member_service.list_members_in_workspace(workspace_id=workspace_id)
    return [convert_member_db_to_response(member) for member in members_db_list]


@router.put("/{member_user_id}/role", response_model=MemberResponse)
async def update_workspace_member_role(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID, # ID of the user whose role is being changed
    role_data: MemberUpdateRole,
    rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.CHANGE_MEMBER_ROLE]))
):
    performing_user = rbac_results.user
    try:
        updated_member_db = member_service.update_member_role(
            user_to_update_id=member_user_id,
            workspace_id=workspace_id,
            new_role_name=role_data.new_role_name,
            performing_user=performing_user
        )
        if not updated_member_db: # Should raise ValueError from service if not found
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found or update failed.")
        return convert_member_db_to_response(updated_member_db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in update_workspace_member_role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update member role.")


@router.delete("/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID, # ID of the user being removed
    rbac_results: RBACResults = Depends(RBACDepends([PermissionEnum.REMOVE_MEMBER]))
):
    performing_user = rbac_results.user
    try:
        success = member_service.remove_member_from_workspace(
            user_to_remove_id=member_user_id,
            workspace_id=workspace_id,
            performing_user=performing_user
        )
        if not success: # Should raise ValueError from service if not found or rule violation
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found or could not be removed.")
    except ValueError as e:
        # Distinguish between not found and other value errors like trying to remove owner
        if "not found" in str(e).lower():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) # e.g. "Cannot remove owner"
    except Exception as e:
        print(f"Unexpected error in remove_workspace_member: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not remove member.")
