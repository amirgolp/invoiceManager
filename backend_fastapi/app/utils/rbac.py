from fastapi import Depends, HTTPException, status, Request
from typing import List, Optional, Set
import uuid

from app.models.user_models import UserInDB
from app.models.role_permission_models import PermissionEnum # Still use Enums for type safety
from app.db.models.role_model_db import Role as RoleDBModel
from app.routers.auth_router import get_current_active_user
from app.services.member_service import member_service # Import the actual member_service

class RBACResults:
    def __init__(self, user: UserInDB, role_name: Optional[str] = None, permissions: Optional[Set[PermissionEnum]] = None):
        self.user = user
        self.role_name = role_name
        self.permissions = permissions if permissions is not None else set()

class RBACDepends:
    def __init__(self, required_permissions: List[PermissionEnum]):
        self.required_permissions = set(required_permissions)

    async def __call__(self,
        request: Request,
        current_user: UserInDB = Depends(get_current_active_user)
    ) -> RBACResults:

        user_role_name: Optional[str] = None
        user_permissions: Set[PermissionEnum] = set()

        workspace_id_str = request.path_params.get("workspace_id")

        if workspace_id_str:
            try:
                workspace_id = uuid.UUID(workspace_id_str)
                # Replace placeholder with call to MemberService
                user_role_name = member_service.get_member_role_name(user_id=current_user.id, workspace_id=workspace_id)

                if user_role_name:
                    role_db = RoleDBModel.objects(name=user_role_name).first()
                    if role_db:
                        user_permissions = set(role_db.permissions)
                        print(f"User {current_user.email} has DB role '{user_role_name}' in workspace {workspace_id} with permissions: {user_permissions}")
                    else:
                        print(f"Warning: Role '{user_role_name}' assigned to user {current_user.email} in workspace {workspace_id} not found in DB.")
                else:
                    print(f"User {current_user.email} is not a member or has no assigned role in workspace {workspace_id}.")

            except ValueError: # Invalid UUID format for workspace_id
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workspace ID format.")
            except Exception as e: # Catch other potential errors from service call
                print(f"Error during RBAC role fetching for user {current_user.email}, workspace {workspace_id_str}: {e}")
                # Depending on policy, might deny or log and continue with no permissions
                # For now, treat as no permissions found.
                pass

        else: # No workspace context
            if not self.required_permissions:
                 return RBACResults(user=current_user, role_name=None, permissions=set())
            # If permissions are required without a workspace context, this implies a global role or misconfiguration.
            # For now, this will lead to a permission denied if user_permissions remains empty.
            print(f"No workspace context for user {current_user.email} for permission check of {self.required_permissions}.")


        if not self.required_permissions.issubset(user_permissions):
            missing_permissions = self.required_permissions - user_permissions
            detail_message = f"User does not have the required permissions: {', '.join(p.value for p in missing_permissions)}."
            if user_role_name:
                detail_message += f" (Role: {user_role_name})"
            else:
                detail_message += " (No specific role or not a member of the workspace)"

            print(f"User {current_user.email} (Role: {user_role_name or 'N/A'}) is missing permissions: {missing_permissions}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_message
            )

        return RBACResults(user=current_user, role_name=user_role_name, permissions=user_permissions)
