import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid

from app.models.role_permission_models import RoleEnum, PermissionEnum
from app.models.task_models import TaskUpdate, TaskStatusEnum, TaskPriorityEnum
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.project_model_db import Project as ProjectDBModel
from app.db.models.task_model_db import Task as TaskDBModel
from app.db.models.role_model_db import Role as RoleDBModel

# Pytest markers
pytestmark = [pytest.mark.integration, pytest.mark.tasks]

# Credentials
OWNER_EMAIL_T = "task_owner_t@example.com"
OWNER_PASS_T = "TaskOwnerPassT123"
OWNER_NAME_T = "Task Owner T"

MEMBER_EMAIL_T = "task_member_t@example.com"
MEMBER_PASS_T = "TaskMemberPassT123"
MEMBER_NAME_T = "Task Member T"

ASSIGNEE_EMAIL_T = "task_assignee_t@example.com" # For assignment tests
ASSIGNEE_PASS_T = "AssigneePassT123"
ASSIGNEE_NAME_T = "Task Assignee T"


@pytest.fixture(scope="function")
def owner_task_token(client: TestClient) -> str:
    if not RoleDBModel.objects(name=RoleEnum.OWNER.value).first(): pytest.skip("OWNER role not found.")
    client.post("/auth/register", json={"email": OWNER_EMAIL_T, "password": OWNER_PASS_T, "name": OWNER_NAME_T})
    return client.post("/auth/login", data={"username": OWNER_EMAIL_T, "password": OWNER_PASS_T}).json()["access_token"]

@pytest.fixture(scope="function")
def member_task_token(client: TestClient, test_ws_t: dict, owner_task_token: str) -> str:
    if not RoleDBModel.objects(name=RoleEnum.MEMBER.value).first(): pytest.skip("MEMBER role not found.")
    client.post("/auth/register", json={"email": MEMBER_EMAIL_T, "password": MEMBER_PASS_T, "name": MEMBER_NAME_T})
    member_token_val = client.post("/auth/login", data={"username": MEMBER_EMAIL_T, "password": MEMBER_PASS_T}).json()["access_token"]

    owner_headers = {"Authorization": f"Bearer {owner_task_token}"}
    ws_id = test_ws_t["id"]
    add_member_payload = {"user_email": MEMBER_EMAIL_T, "role_name": RoleEnum.MEMBER.value}
    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_member_payload)
    return member_token_val

@pytest.fixture(scope="function")
def assignee_user_db_and_token(client: TestClient, test_ws_t: dict, owner_task_token: str) -> dict:
    # Registers and logs in the assignee, also adds them as a MEMBER to the workspace
    client.post("/auth/register", json={"email": ASSIGNEE_EMAIL_T, "password": ASSIGNEE_PASS_T, "name": ASSIGNEE_NAME_T})
    token = client.post("/auth/login", data={"username": ASSIGNEE_EMAIL_T, "password": ASSIGNEE_PASS_T}).json()["access_token"]
    user_db = UserDBModel.objects(email=ASSIGNEE_EMAIL_T).first()

    # Add assignee as a member to the workspace so they can be assigned tasks within it
    owner_headers = {"Authorization": f"Bearer {owner_task_token}"}
    ws_id = test_ws_t["id"]
    add_member_payload = {"user_email": ASSIGNEE_EMAIL_T, "role_name": RoleEnum.MEMBER.value}
    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_member_payload)

    return {"token": token, "db_obj": user_db, "id_str": str(user_db.id)}


@pytest.fixture(scope="function")
def test_ws_t(client: TestClient, owner_task_token: str) -> dict: # Renamed to avoid clash
    headers = {"Authorization": f"Bearer {owner_task_token}"}
    ws_name = f"TaskTestWS_T_{uuid.uuid4()}"
    response = client.post("/workspaces", headers=headers, json={"name": ws_name})
    return {"id": response.json()["id"], "owner_headers": headers}

@pytest.fixture(scope="function")
def test_project_t(client: TestClient, test_ws_t: dict) -> dict: # Renamed
    ws_id = test_ws_t["id"]
    owner_headers = test_ws_t["owner_headers"]
    project_name = f"TaskTestProject_T_{uuid.uuid4()}"
    response = client.post(f"/workspaces/{ws_id}/projects", headers=owner_headers, json={"name": project_name})
    return {"id": response.json()["id"], "ws_id": ws_id, "owner_headers": owner_headers}

@pytest.fixture(scope="function")
def created_task(client: TestClient, test_project_t: dict) -> dict: # Renamed
    ws_id = test_project_t["ws_id"]
    project_id = test_project_t["id"]
    owner_headers = test_project_t["owner_headers"]
    task_payload = {"title": f"Gettable Task T {uuid.uuid4()}"}
    response = client.post(f"/workspaces/{ws_id}/projects/{project_id}/tasks", headers=owner_headers, json=task_payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()

# --- CREATE, GET, LIST Tests (adapted from previous, using new fixture names) ---
def test_create_task_success(client: TestClient, test_project_t: dict, owner_task_token: str):
    ws_id, project_id, headers = test_project_t["ws_id"], test_project_t["id"], {"Authorization": f"Bearer {owner_task_token}"}
    task_payload = {"title": "My First Task T", "description": "Details here"}
    response = client.post(f"/workspaces/{ws_id}/projects/{project_id}/tasks", headers=headers, json=task_payload)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["title"] == "My First Task T" and data["project_id"] == project_id

def test_get_task_success_as_owner(client: TestClient, test_project_t: dict, created_task: dict, owner_task_token: str):
    ws_id, project_id, task_id, headers = test_project_t["ws_id"], test_project_t["id"], created_task["id"], {"Authorization": f"Bearer {owner_task_token}"}
    response = client.get(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["id"] == task_id

def test_list_tasks_in_project_success(client: TestClient, test_project_t: dict, created_task: dict, owner_task_token: str):
    ws_id, project_id, headers = test_project_t["ws_id"], test_project_t["id"], {"Authorization": f"Bearer {owner_task_token}"}
    client.post(f"/workspaces/{ws_id}/projects/{project_id}/tasks", headers=headers, json={"title": "Task Two T"})
    response = client.get(f"/workspaces/{ws_id}/projects/{project_id}/tasks", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list) and len(data) >= 2

# --- UPDATE Task Tests ---
def test_update_task_success_as_owner(client: TestClient, test_project_t: dict, created_task: dict, owner_task_token: str, assignee_user_db_and_token: dict):
    ws_id, project_id, task_id, headers = test_project_t["ws_id"], test_project_t["id"], created_task["id"], {"Authorization": f"Bearer {owner_task_token}"}
    assignee_id = assignee_user_db_and_token["id_str"]

    update_payload = TaskUpdate(
        title="Updated Task Title",
        description="New task description.",
        status=TaskStatusEnum.IN_PROGRESS,
        priority=TaskPriorityEnum.HIGH,
        assigned_to_id=uuid.UUID(assignee_id) # Ensure UUID type if model expects it
    ).model_dump(exclude_unset=True)

    response = client.put(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["title"] == "Updated Task Title"
    assert data["description"] == "New task description."
    assert data["status"] == TaskStatusEnum.IN_PROGRESS.value
    assert data["priority"] == TaskPriorityEnum.HIGH.value
    assert data["assigned_to_id"] == assignee_id

def test_update_task_unassign_and_clear_due_date(client: TestClient, test_project_t: dict, created_task: dict, owner_task_token: str, assignee_user_db_and_token: dict):
    ws_id, project_id, task_id, headers = test_project_t["ws_id"], test_project_t["id"], created_task["id"], {"Authorization": f"Bearer {owner_task_token}"}
    assignee_id = assignee_user_db_and_token["id_str"]

    # First, assign a user and set a due date
    initial_update_payload = {"assigned_to_id": assignee_id, "due_date": "2025-01-01T00:00:00Z"} # Use ISO format with Z for UTC
    put_response = client.put(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers, json=initial_update_payload)
    assert put_response.status_code == status.HTTP_200_OK, f"Initial update failed: {put_response.text}"

    update_payload = TaskUpdate(assigned_to_id=None, due_date=None).model_dump(exclude_none=False) # exclude_none=False to send explicit nulls

    response = client.put(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["assigned_to_id"] is None
    assert data["due_date"] is None


def test_update_task_forbidden_as_member_without_edit_task_perm(client: TestClient, test_project_t: dict, created_task: dict, member_task_token: str):
    # This test assumes the default MEMBER role does NOT have EDIT_TASK.
    # My current seeded MEMBER role does NOT have EDIT_TASK.
    ws_id, project_id, task_id, headers = test_project_t["ws_id"], test_project_t["id"], created_task["id"], {"Authorization": f"Bearer {member_task_token}"}
    update_payload = TaskUpdate(title="Member Edit Attempt").model_dump(exclude_unset=True)

    response = client.put(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text

def test_update_task_not_found(client: TestClient, test_project_t: dict, owner_task_token: str):
    ws_id, project_id, headers = test_project_t["ws_id"], test_project_t["id"], {"Authorization": f"Bearer {owner_task_token}"}
    non_existent_task_id = str(uuid.uuid4())
    update_payload = TaskUpdate(title="Update Non Existent").model_dump(exclude_unset=True)
    response = client.put(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{non_existent_task_id}", headers=headers, json=update_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text

# --- DELETE Task Tests ---
def test_delete_task_success_as_owner(client: TestClient, test_project_t: dict, created_task: dict, owner_task_token: str):
    ws_id, project_id, task_id, headers = test_project_t["ws_id"], test_project_t["id"], created_task["id"], {"Authorization": f"Bearer {owner_task_token}"}

    delete_response = client.delete(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, delete_response.text
    assert TaskDBModel.objects(id=task_id).count() == 0

    get_response = client.get(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_task_forbidden_as_member_without_delete_task_perm(client: TestClient, test_project_t: dict, created_task: dict, member_task_token: str):
    # Assumes default MEMBER role does NOT have DELETE_TASK.
    # My current seeded MEMBER role does NOT have DELETE_TASK.
    ws_id, project_id, task_id, headers = test_project_t["ws_id"], test_project_t["id"], created_task["id"], {"Authorization": f"Bearer {member_task_token}"}
    response = client.delete(f"/workspaces/{ws_id}/projects/{project_id}/tasks/{task_id}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
