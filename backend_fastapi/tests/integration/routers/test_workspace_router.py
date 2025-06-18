import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid

from app.models.role_permission_models import RoleEnum, PermissionEnum
from app.models.workspace_models import WorkspaceUpdate
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.project_model_db import Project as ProjectDBModel # For testing cascade delete
from app.db.models.task_model_db import Task as TaskDBModel # For testing cascade delete
from app.db.models.role_model_db import Role as RoleDBModel
from app.services.member_service import member_service # To add members for tests

# Pytest markers
pytestmark = [pytest.mark.integration, pytest.mark.workspaces]

# Test User Credentials
TEST_USER_EMAIL_W = "ws_user_owner@example.com" # Renamed for clarity
TEST_USER_PASSWORD_W = "WsSecurePassword123"
TEST_USER_NAME_W = "Workspace Owner User"

TEST_MEMBER_USER_EMAIL_W = "ws_member_user@example.com"
TEST_MEMBER_USER_PASSWORD_W = "MemberPassword123"
TEST_MEMBER_USER_NAME_W = "Workspace Member User"

TEST_NON_MEMBER_USER_EMAIL_W = "ws_non_member@example.com"
TEST_NON_MEMBER_USER_PASSWORD_W = "NonMemberPass123"
TEST_NON_MEMBER_USER_NAME_W = "Non Member User"


@pytest.fixture(scope="function")
def owner_user_token(client: TestClient) -> str:
    if not RoleDBModel.objects(name=RoleEnum.OWNER.value).first():
        pytest.skip("OWNER role not found in DB. Run seeder or ensure test DB is pre-seeded.")

    payload = {"email": TEST_USER_EMAIL_W, "password": TEST_USER_PASSWORD_W, "name": TEST_USER_NAME_W}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED, f"Owner registration failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="function")
def member_user_token(client: TestClient) -> str:
    payload = {"email": TEST_MEMBER_USER_EMAIL_W, "password": TEST_MEMBER_USER_PASSWORD_W, "name": TEST_MEMBER_USER_NAME_W}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED, f"Member user registration failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="function")
def non_member_user_token(client: TestClient) -> str:
    payload = {"email": TEST_NON_MEMBER_USER_EMAIL_W, "password": TEST_NON_MEMBER_USER_PASSWORD_W, "name": TEST_NON_MEMBER_USER_NAME_W}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED, f"Non-member user registration failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def created_workspace_by_owner(client: TestClient, owner_user_token: str) -> dict:
    headers = {"Authorization": f"Bearer {owner_user_token}"}
    ws_name = f"Test WS by Owner {uuid.uuid4()}" # Unique name
    workspace_payload = {"name": ws_name, "description": "Workspace created by owner fixture"}
    response = client.post("/workspaces", headers=headers, json=workspace_payload)
    assert response.status_code == status.HTTP_201_CREATED, f"Workspace creation by owner failed: {response.text}"
    workspace_data = response.json()

    # Get owner user DB object for later use if needed (e.g. for adding member)
    owner_user_db = UserDBModel.objects(email=TEST_USER_EMAIL_W).first()
    assert owner_user_db is not None

    return {"data": workspace_data, "owner_token": owner_user_token, "owner_headers": headers, "owner_user_db": owner_user_db}

# ... (test_create_workspace_success, test_create_workspace_no_token from previous version) ...
def test_create_workspace_success(client: TestClient, owner_user_token: str):
    headers = {"Authorization": f"Bearer {owner_user_token}"}
    workspace_payload = {"name": "My Awesome Workspace", "description": "Desc for awesome ws."}
    response = client.post("/workspaces", headers=headers, json=workspace_payload)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["name"] == "My Awesome Workspace"
    me_response = client.get("/auth/users/me", headers=headers)
    creator_id = me_response.json()["id"]
    assert data["owner_id"] == creator_id
    member_entry = MemberDBModel.objects(user=creator_id, workspace=data["id"]).first()
    assert member_entry is not None and member_entry.role_name == RoleEnum.OWNER.value

def test_get_workspace_by_id_as_owner(client: TestClient, created_workspace_by_owner: dict):
    workspace_id = created_workspace_by_owner["data"]["id"]
    headers = created_workspace_by_owner["owner_headers"]
    response = client.get(f"/workspaces/{workspace_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == workspace_id

def test_get_workspace_by_id_as_member(client: TestClient, created_workspace_by_owner: dict, member_user_token: str):
    workspace_id = created_workspace_by_owner["data"]["id"]
    owner_headers = created_workspace_by_owner["owner_headers"]

    # Add member_user to this workspace with MEMBER role (by owner)
    member_user_db = UserDBModel.objects(email=TEST_MEMBER_USER_EMAIL_W).first()
    assert member_user_db is not None

    add_member_payload = {"user_email": TEST_MEMBER_USER_EMAIL_W, "role_name": RoleEnum.MEMBER.value}
    add_response = client.post(f"/workspaces/{workspace_id}/members", headers=owner_headers, json=add_member_payload)
    assert add_response.status_code == status.HTTP_201_CREATED, f"Failed to add member: {add_response.text}"

    member_headers = {"Authorization": f"Bearer {member_user_token}"}
    response = client.get(f"/workspaces/{workspace_id}", headers=member_headers)
    assert response.status_code == status.HTTP_200_OK # MEMBER role has VIEW_ONLY by default
    assert response.json()["id"] == workspace_id

def test_get_workspace_by_id_as_non_member(client: TestClient, created_workspace_by_owner: dict, non_member_user_token: str):
    workspace_id = created_workspace_by_owner["data"]["id"]
    non_member_headers = {"Authorization": f"Bearer {non_member_user_token}"}
    response = client.get(f"/workspaces/{workspace_id}", headers=non_member_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN # RBAC should deny

def test_get_workspace_by_id_not_found(client: TestClient, owner_user_token: str):
    headers = {"Authorization": f"Bearer {owner_user_token}"}
    random_uuid_str = str(uuid.uuid4())
    response = client.get(f"/workspaces/{random_uuid_str}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

# ... (test_list_user_workspaces_success, test_list_user_workspaces_no_workspaces from previous) ...
def test_list_user_workspaces_success(client: TestClient, created_workspace_by_owner: dict):
    headers = created_workspace_by_owner["owner_headers"]
    response = client.get("/workspaces", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list) and len(data) >= 1
    assert any(ws["id"] == created_workspace_by_owner["data"]["id"] for ws in data)

def test_update_workspace_success_as_owner(client: TestClient, created_workspace_by_owner: dict):
    workspace_id = created_workspace_by_owner["data"]["id"]
    headers = created_workspace_by_owner["owner_headers"]
    update_payload = WorkspaceUpdate(name="Updated Workspace Name", description="Updated description.").model_dump()

    response = client.put(f"/workspaces/{workspace_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["name"] == "Updated Workspace Name"
    assert data["description"] == "Updated description."
    assert data["id"] == workspace_id

def test_update_workspace_forbidden_as_member(client: TestClient, created_workspace_by_owner: dict, member_user_token: str):
    workspace_id = created_workspace_by_owner["data"]["id"]
    owner_headers = created_workspace_by_owner["owner_headers"]

    # Add member_user to this workspace with MEMBER role
    client.post(f"/workspaces/{workspace_id}/members", headers=owner_headers, json={"user_email": TEST_MEMBER_USER_EMAIL_W, "role_name": RoleEnum.MEMBER.value})

    member_headers = {"Authorization": f"Bearer {member_user_token}"}
    update_payload = WorkspaceUpdate(name="Attempted Update by Member").model_dump()
    response = client.put(f"/workspaces/{workspace_id}", headers=member_headers, json=update_payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN # MEMBER role should not have EDIT_WORKSPACE

def test_delete_workspace_success_as_owner(client: TestClient, created_workspace_by_owner: dict):
    workspace_id = created_workspace_by_owner["data"]["id"]
    owner_user_db = created_workspace_by_owner["owner_user_db"]
    headers = created_workspace_by_owner["owner_headers"]

    # Optionally, create a project and task in it to test cascade delete
    project_payload = {"name": "Project to be deleted"}
    proj_res = client.post(f"/workspaces/{workspace_id}/projects", headers=headers, json=project_payload)
    assert proj_res.status_code == status.HTTP_201_CREATED
    project_id = proj_res.json()["id"]

    task_payload = {"title": "Task to be deleted"}
    task_res = client.post(f"/workspaces/{workspace_id}/projects/{project_id}/tasks", headers=headers, json=task_payload)
    assert task_res.status_code == status.HTTP_201_CREATED
    task_id = task_res.json()["id"]

    delete_response = client.delete(f"/workspaces/{workspace_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, delete_response.text

    # Verify workspace is deleted
    get_response = client.get(f"/workspaces/{workspace_id}", headers=headers)
    # For owner who just deleted it, RBAC might pass if role isn't checked against live workspace membership for this path
    # However, the service itself should return 404. If RBAC runs first and can't find a role for a deleted workspace, it might 403.
    # The current RBAC placeholder defaults to MEMBER if role not found, so VIEW_ONLY might pass.
    # This depends on exact RBAC implementation details for deleted/non-existent workspaces.
    # For now, expecting 404 from the service layer.
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

    # Verify member entry for owner is deleted
    assert MemberDBModel.objects(user=owner_user_db.id, workspace=workspace_id).count() == 0
    # Verify project is deleted
    assert ProjectDBModel.objects(id=project_id).count() == 0
    # Verify task is deleted (due to project model's cascade rule or explicit service delete)
    assert TaskDBModel.objects(id=task_id).count() == 0


def test_delete_workspace_forbidden_as_member(client: TestClient, created_workspace_by_owner: dict, member_user_token: str):
    workspace_id = created_workspace_by_owner["data"]["id"]
    owner_headers = created_workspace_by_owner["owner_headers"]

    client.post(f"/workspaces/{workspace_id}/members", headers=owner_headers, json={"user_email": TEST_MEMBER_USER_EMAIL_W, "role_name": RoleEnum.MEMBER.value})

    member_headers = {"Authorization": f"Bearer {member_user_token}"}
    response = client.delete(f"/workspaces/{workspace_id}", headers=member_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
