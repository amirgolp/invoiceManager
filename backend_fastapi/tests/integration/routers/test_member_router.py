import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid

from app.models.role_permission_models import RoleEnum, PermissionEnum
from app.models.member_models import MemberAdd, MemberUpdateRole
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.role_model_db import Role as RoleDBModel

# Pytest markers
pytestmark = [pytest.mark.integration, pytest.mark.members]

# Credentials
OWNER_EMAIL_M = "member_owner@example.com"
OWNER_PASS_M = "MemberOwnerPass123"
OWNER_NAME_M = "Member Owner"

USER_TO_ADD_EMAIL_M = "member_add@example.com"
USER_TO_ADD_PASS_M = "MemberAddPass123"
USER_TO_ADD_NAME_M = "User To Add"

USER_ALREADY_MEMBER_EMAIL_M = "member_already@example.com" # For specific tests
USER_ALREADY_MEMBER_PASS_M = "AlreadyMemberPass123"
USER_ALREADY_MEMBER_NAME_M = "Already Member"


@pytest.fixture(scope="function")
def owner_member_token(client: TestClient) -> str:
    if not RoleDBModel.objects(name=RoleEnum.OWNER.value).first(): pytest.skip("OWNER role not found.")
    client.post("/auth/register", json={"email": OWNER_EMAIL_M, "password": OWNER_PASS_M, "name": OWNER_NAME_M})
    return client.post("/auth/login", data={"username": OWNER_EMAIL_M, "password": OWNER_PASS_M}).json()["access_token"]

@pytest.fixture(scope="function")
def user_to_add_details(client: TestClient) -> dict: # Provides DB object and token
    client.post("/auth/register", json={"email": USER_TO_ADD_EMAIL_M, "password": USER_TO_ADD_PASS_M, "name": USER_TO_ADD_NAME_M})
    token = client.post("/auth/login", data={"username": USER_TO_ADD_EMAIL_M, "password": USER_TO_ADD_PASS_M}).json()["access_token"]
    user_db = UserDBModel.objects(email=USER_TO_ADD_EMAIL_M).first()
    return {"token": token, "db_obj": user_db, "email": USER_TO_ADD_EMAIL_M, "id_str": str(user_db.id)}

@pytest.fixture(scope="function")
def test_ws_for_members(client: TestClient, owner_member_token: str) -> dict:
    headers = {"Authorization": f"Bearer {owner_member_token}"}
    ws_name = f"MemberTestWS_{uuid.uuid4()}"
    response = client.post("/workspaces", headers=headers, json={"name": ws_name})
    assert response.status_code == status.HTTP_201_CREATED
    ws_data = response.json()
    owner_db = UserDBModel.objects(email=OWNER_EMAIL_M).first()
    return {"id": ws_data["id"], "owner_headers": headers, "owner_db": owner_db}

# --- ADD Member Tests ---
def test_add_member_success(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    user_to_add_email = user_to_add_details["email"]

    add_payload = MemberAdd(user_email=user_to_add_email, role_name=RoleEnum.MEMBER.value).model_dump()
    response = client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_payload)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["user"]["email"] == user_to_add_email
    assert data["role_name"] == RoleEnum.MEMBER.value
    assert data["workspace_id"] == ws_id

    # Verify in DB
    user_db_obj = user_to_add_details["db_obj"]
    assert MemberDBModel.objects(user=user_db_obj.id, workspace=ws_id, role_name=RoleEnum.MEMBER.value).count() == 1

def test_add_member_user_not_found(client: TestClient, test_ws_for_members: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    add_payload = MemberAdd(user_email="nonexistent@example.com", role_name=RoleEnum.MEMBER.value).model_dump()
    response = client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text
    assert "User with email nonexistent@example.com not found" in response.json()["detail"]

def test_add_member_invalid_role_name(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    user_to_add_email = user_to_add_details["email"]
    add_payload = MemberAdd(user_email=user_to_add_email, role_name="INVALID_ROLE").model_dump()
    response = client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert "Role 'INVALID_ROLE' does not exist" in response.json()["detail"]

def test_add_member_already_exists(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    user_to_add_email = user_to_add_details["email"]

    # Add once
    add_payload = MemberAdd(user_email=user_to_add_email, role_name=RoleEnum.MEMBER.value).model_dump()
    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_payload)

    # Attempt to add again
    response = client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=add_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert f"User {user_to_add_email} is already a member" in response.json()["detail"]

def test_add_member_no_permission(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict, member_token: str): # Assuming member_token is from a user not owner of test_ws_for_members
    # Register and login a 'member' user who will try to add another user
    # This 'member_token' user is NOT yet part of test_ws_for_members.
    # To test ADD_MEMBER permission, the 'member_token' user needs to be part of test_ws_for_members
    # but with a role that LACKS ADD_MEMBER permission (e.g. a custom role, or if MEMBER role lacks it)
    # My default seeded MEMBER role does NOT have ADD_MEMBER. So, this test is valid if member_token user is added as MEMBER.

    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"] # Owner adds the 'member_token' user first

    # Register the user for member_token if not implicitly done by fixture
    # This part is tricky because member_token fixture might not exist or might not be the intended one.
    # For this test, let's create a specific 'attacker' user and add them as MEMBER.
    attacker_email = "attacker_member@example.com"
    client.post("/auth/register", json={"email": attacker_email, "password": "password", "name": "Attacker Member"})
    attacker_login_res = client.post("/auth/login", data={"username": attacker_email, "password": "password"})
    attacker_token = attacker_login_res.json()["access_token"]

    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json={"user_email": attacker_email, "role_name": RoleEnum.MEMBER.value})

    attacker_headers = {"Authorization": f"Bearer {attacker_token}"}
    user_to_add_email = user_to_add_details["email"] # This user is different from MEMBER_EMAIL_P
    add_payload = MemberAdd(user_email=user_to_add_email, role_name=RoleEnum.MEMBER.value).model_dump()

    response = client.post(f"/workspaces/{ws_id}/members", headers=attacker_headers, json=add_payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text


# --- LIST Members Tests ---
def test_list_members_success(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]

    # Add user_to_add
    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=MemberAdd(user_email=user_to_add_details["email"], role_name=RoleEnum.MEMBER.value).model_dump())

    response = client.get(f"/workspaces/{ws_id}/members", headers=owner_headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2 # Owner + user_to_add
    emails = [m["user"]["email"] for m in data]
    assert OWNER_EMAIL_M in emails
    assert user_to_add_details["email"] in emails

# --- UPDATE Member Role Tests ---
def test_update_member_role_success(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    user_to_update_id = user_to_add_details["db_obj"].id

    # Add user first as MEMBER
    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=MemberAdd(user_email=user_to_add_details["email"], role_name=RoleEnum.MEMBER.value).model_dump())

    update_payload = MemberUpdateRole(new_role_name=RoleEnum.ADMIN.value).model_dump() # Promote to ADMIN
    response = client.put(f"/workspaces/{ws_id}/members/{user_to_update_id}/role", headers=owner_headers, json=update_payload)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["user"]["id"] == str(user_to_update_id)
    assert data["role_name"] == RoleEnum.ADMIN.value

def test_update_member_role_cannot_demote_sole_owner(client: TestClient, test_ws_for_members: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    owner_id = test_ws_for_members["owner_db"].id

    update_payload = MemberUpdateRole(new_role_name=RoleEnum.ADMIN.value).model_dump()
    response = client.put(f"/workspaces/{ws_id}/members/{owner_id}/role", headers=owner_headers, json=update_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text # Service raises ValueError
    assert "Cannot change the role of the sole owner to a non-owner role" in response.json()["detail"]

def test_update_member_role_invalid_role(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    user_to_update_id = user_to_add_details["db_obj"].id
    client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=MemberAdd(user_email=user_to_add_details["email"], role_name=RoleEnum.MEMBER.value).model_dump())

    update_payload = MemberUpdateRole(new_role_name="FAKE_ROLE").model_dump()
    response = client.put(f"/workspaces/{ws_id}/members/{user_to_update_id}/role", headers=owner_headers, json=update_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert "Role 'FAKE_ROLE' does not exist" in response.json()["detail"]


# --- REMOVE Member Tests ---
def test_remove_member_success(client: TestClient, test_ws_for_members: dict, user_to_add_details: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    user_to_remove_id = user_to_add_details["db_obj"].id

    # Add user first
    add_res = client.post(f"/workspaces/{ws_id}/members", headers=owner_headers, json=MemberAdd(user_email=user_to_add_details["email"], role_name=RoleEnum.MEMBER.value).model_dump())
    assert add_res.status_code == status.HTTP_201_CREATED

    response = client.delete(f"/workspaces/{ws_id}/members/{user_to_remove_id}", headers=owner_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text
    assert MemberDBModel.objects(user=user_to_remove_id, workspace=ws_id).count() == 0

def test_remove_member_cannot_remove_owner(client: TestClient, test_ws_for_members: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    owner_id = test_ws_for_members["owner_db"].id

    response = client.delete(f"/workspaces/{ws_id}/members/{owner_id}", headers=owner_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert "Cannot remove the workspace owner" in response.json()["detail"]

def test_remove_non_existent_member(client: TestClient, test_ws_for_members: dict):
    ws_id = test_ws_for_members["id"]
    owner_headers = test_ws_for_members["owner_headers"]
    non_existent_user_id = str(uuid.uuid4())
    response = client.delete(f"/workspaces/{ws_id}/members/{non_existent_user_id}", headers=owner_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text
    assert "Member not found or could not be removed" in response.json()["detail"]
