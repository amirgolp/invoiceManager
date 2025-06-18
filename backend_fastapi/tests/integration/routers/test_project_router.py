import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid

from app.models.role_permission_models import RoleEnum, PermissionEnum
from app.models.project_models import ProjectUpdate
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.project_model_db import Project as ProjectDBModel
from app.db.models.task_model_db import Task as TaskDBModel # For testing cascade delete
from app.db.models.role_model_db import Role as RoleDBModel

# Pytest markers
pytestmark = [pytest.mark.integration, pytest.mark.projects]

# Credentials
OWNER_EMAIL_P = "project_owner_p@example.com"
OWNER_PASS_P = "OwnerPassP123"
OWNER_NAME_P = "Project Owner P"

MEMBER_EMAIL_P = "project_member_p@example.com"
MEMBER_PASS_P = "MemberPassP123"
MEMBER_NAME_P = "Project Member P"

# Fixtures for user tokens (owner_token, member_token, non_member_project_token)
# and test_ws are assumed to be similar to the previous subtask's version.
# For brevity, I'll redefine them here if they need slight adjustments for project tests.

@pytest.fixture(scope="function")
def owner_token(client: TestClient) -> str: # Generic name for reusability
    if not RoleDBModel.objects(name=RoleEnum.OWNER.value).first():
        pytest.skip("OWNER role not found. Seed database for tests.")
    client.post("/auth/register", json={"email": OWNER_EMAIL_P, "password": OWNER_PASS_P, "name": OWNER_NAME_P})
    response = client.post("/auth/login", data={"username": OWNER_EMAIL_P, "password": OWNER_PASS_P})
    assert response.status_code == status.HTTP_200_OK, "Owner login failed"
    return response.json()["access_token"]

@pytest.fixture(scope="function")
def member_token(client: TestClient) -> str:
    if not RoleDBModel.objects(name=RoleEnum.MEMBER.value).first():
        pytest.skip("MEMBER role not found. Seed database for tests.")
    client.post("/auth/register", json={"email": MEMBER_EMAIL_P, "password": MEMBER_PASS_P, "name": MEMBER_NAME_P})
    response = client.post("/auth/login", data={"username": MEMBER_EMAIL_P, "password": MEMBER_PASS_P})
    assert response.status_code == status.HTTP_200_OK, "Member login failed"
    return response.json()["access_token"]

@pytest.fixture(scope="function")
def test_ws(client: TestClient, owner_token: str) -> dict: # Generic name
    headers = {"Authorization": f"Bearer {owner_token}"}
    ws_name = f"ProjectTestWS_{uuid.uuid4()}"
    response = client.post("/workspaces", headers=headers, json={"name": ws_name, "description": "WS for project tests"})
    assert response.status_code == status.HTTP_201_CREATED, "Workspace creation failed"
    ws_data = response.json()
    return {"id": ws_data["id"], "owner_headers": headers}

@pytest.fixture(scope="function")
def test_project(client: TestClient, test_ws: dict) -> dict:
    ws_id = test_ws["id"]
    owner_headers = test_ws["owner_headers"]
    project_name = f"TestProject_{uuid.uuid4()}"
    project_payload = {"name": project_name, "description": "Initial project description"}
    response = client.post(f"/workspaces/{ws_id}/projects", headers=owner_headers, json=project_payload)
    assert response.status_code == status.HTTP_201_CREATED, f"Project creation failed: {response.text}"
    return response.json()

# ... (Create, Get Single, List tests from previous setup, ensure they use new fixture names like owner_token, test_ws)

def test_create_project_success(client: TestClient, test_ws: dict, owner_token: str):
    ws_id = test_ws["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    project_payload = {"name": "Project Alpha", "description": "First project"}
    response = client.post(f"/workspaces/{ws_id}/projects", headers=headers, json=project_payload)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["name"] == "Project Alpha"
    assert data["workspace_id"] == ws_id
    assert ProjectDBModel.objects(id=data["id"]).count() == 1

def test_get_project_as_owner(client: TestClient, test_ws: dict, test_project: dict, owner_token: str):
    ws_id = test_ws["id"]
    project_id = test_project["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = client.get(f"/workspaces/{ws_id}/projects/{project_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["id"] == project_id

def test_list_projects_in_workspace(client: TestClient, test_ws: dict, test_project: dict, owner_token: str):
    ws_id = test_ws["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    # test_project fixture already created one. Create another for list test.
    client.post(f"/workspaces/{ws_id}/projects", headers=headers, json={"name": "Project Beta"})
    response = client.get(f"/workspaces/{ws_id}/projects", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    project_names = [p["name"] for p in data]
    assert test_project["name"] in project_names
    assert "Project Beta" in project_names

# --- UPDATE Project Tests ---
def test_update_project_success_as_owner(client: TestClient, test_ws: dict, test_project: dict, owner_token: str):
    ws_id = test_ws["id"]
    project_id = test_project["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    update_payload = ProjectUpdate(name="Updated Project Name", description="New desc.", emoji="🚀").model_dump(exclude_unset=True)

    response = client.put(f"/workspaces/{ws_id}/projects/{project_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["name"] == "Updated Project Name"
    assert data["description"] == "New desc."
    assert data["emoji"] == "🚀"
    assert data["id"] == project_id

def test_update_project_partial_success(client: TestClient, test_ws: dict, test_project: dict, owner_token: str):
    ws_id = test_ws["id"]
    project_id = test_project["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    update_payload = ProjectUpdate(name="Partially Updated Name").model_dump(exclude_unset=True) # Only name

    response = client.put(f"/workspaces/{ws_id}/projects/{project_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["name"] == "Partially Updated Name"
    assert data["description"] == test_project["description"] # Description should be unchanged

def test_update_project_forbidden_as_member(client: TestClient, test_ws: dict, test_project: dict, owner_token:str, member_token: str):
    ws_id = test_ws["id"]
    project_id = test_project["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Add member to workspace
    add_member_payload = {"user_email": MEMBER_EMAIL_P, "role_name": RoleEnum.MEMBER.value}
    add_member_res = client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_member_payload)
    assert add_member_res.status_code == status.HTTP_201_CREATED

    member_headers = {"Authorization": f"Bearer {member_token}"}
    update_payload = ProjectUpdate(name="Member Update Attempt").model_dump(exclude_unset=True)
    response = client.put(f"/workspaces/{ws_id}/projects/{project_id}", headers=member_headers, json=update_payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text # MEMBER should not have EDIT_PROJECT

def test_update_project_not_found(client: TestClient, test_ws: dict, owner_token: str):
    ws_id = test_ws["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    non_existent_project_id = str(uuid.uuid4())
    update_payload = ProjectUpdate(name="Update Non Existent").model_dump(exclude_unset=True)
    response = client.put(f"/workspaces/{ws_id}/projects/{non_existent_project_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text

# --- DELETE Project Tests ---
def test_delete_project_success_as_owner(client: TestClient, test_ws: dict, test_project: dict, owner_token: str):
    ws_id = test_ws["id"]
    project_id = test_project["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}

    # Optionally create tasks to test cascade delete from project service
    task_payload = {"title": "Task in deleted project"}
    task_res = client.post(f"/workspaces/{ws_id}/projects/{project_id}/tasks", headers=headers, json=task_payload)
    assert task_res.status_code == status.HTTP_201_CREATED, task_res.text
    task_id = task_res.json()["id"]
    assert TaskDBModel.objects(id=task_id).count() == 1


    delete_response = client.delete(f"/workspaces/{ws_id}/projects/{project_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, delete_response.text

    # Verify project is deleted from DB
    assert ProjectDBModel.objects(id=project_id).count() == 0
    # Verify task is also deleted due to cascade logic in ProjectService.delete_project
    assert TaskDBModel.objects(id=task_id).count() == 0

    # Verify project is not retrievable
    get_response = client.get(f"/workspaces/{ws_id}/projects/{project_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_project_forbidden_as_member(client: TestClient, test_ws: dict, test_project: dict, owner_token:str, member_token: str):
    ws_id = test_ws["id"]
    project_id = test_project["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    add_member_payload = {"user_email": MEMBER_EMAIL_P, "role_name": RoleEnum.MEMBER.value}
    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_member_payload)

    member_headers = {"Authorization": f"Bearer {member_token}"}
    response = client.delete(f"/workspaces/{ws_id}/projects/{project_id}", headers=member_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text

def test_delete_project_not_found(client: TestClient, test_ws: dict, owner_token: str):
    ws_id = test_ws["id"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    non_existent_project_id = str(uuid.uuid4())
    response = client.delete(f"/workspaces/{ws_id}/projects/{non_existent_project_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text
