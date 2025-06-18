import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.config.settings import settings
from app.db.redis_db import is_token_jti_valid
from jose import jwt
import time

pytestmark = [pytest.mark.integration, pytest.mark.auth]

TEST_USER_EMAIL = "testuser@example.com"
TEST_USER_PASSWORD = "SecurePassword123"
TEST_USER_NAME = "Test User"

@pytest.fixture(scope="function")
def registered_user_token(client: TestClient) -> str:
    registration_payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "name": TEST_USER_NAME
    }
    response = client.post("/auth/register", json=registration_payload)
    assert response.status_code == status.HTTP_201_CREATED
    token_data = response.json()
    assert "access_token" in token_data
    return token_data["access_token"]

def test_register_user_success(client: TestClient):
    payload = {
        "email": "newuser@example.com",
        "password": "NewPassword123",
        "name": "New User"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["name"] == "New User"
    assert "id" in data["user"]
    decoded_token = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert "jti" in decoded_token
    assert is_token_jti_valid(decoded_token["jti"]) is True

def test_register_user_duplicate_email(client: TestClient, registered_user_token):
    payload = {
        "email": TEST_USER_EMAIL,
        "password": "AnotherPassword",
        "name": "Another User"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response.json()["detail"]

def test_login_user_success(client: TestClient, registered_user_token):
    login_payload = {
        "username": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    }
    response = client.post("/auth/login", data=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == TEST_USER_EMAIL
    decoded_token = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert "jti" in decoded_token
    assert is_token_jti_valid(decoded_token["jti"]) is True

def test_login_user_incorrect_password(client: TestClient, registered_user_token):
    login_payload = {
        "username": TEST_USER_EMAIL,
        "password": "WrongPassword"
    }
    response = client.post("/auth/login", data=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect username or password" in response.json()["detail"]

def test_login_user_not_found(client: TestClient):
    login_payload = {
        "username": "nonexistent@example.com",
        "password": "anypassword"
    }
    response = client.post("/auth/login", data=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect username or password" in response.json()["detail"]

def test_read_users_me_success(client: TestClient, registered_user_token):
    headers = {"Authorization": f"Bearer {registered_user_token}"}
    response = client.get("/auth/users/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == TEST_USER_EMAIL
    assert data["name"] == TEST_USER_NAME

def test_read_users_me_no_token(client: TestClient):
    response = client.get("/auth/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"

def test_read_users_me_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer invalidtokenstring"}
    response = client.get("/auth/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]

def test_logout_user_success(client: TestClient, registered_user_token):
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    me_response = client.get("/auth/users/me", headers=headers)
    assert me_response.status_code == status.HTTP_200_OK

    decoded_token_before_logout = jwt.decode(registered_user_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti_to_revoke = decoded_token_before_logout["jti"]
    assert is_token_jti_valid(jti_to_revoke) is True

    logout_response = client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == status.HTTP_200_OK
    assert "Token has been revoked" in logout_response.json()["message"]

    assert is_token_jti_valid(jti_to_revoke) is False

    me_response_after_logout = client.get("/auth/users/me", headers=headers)
    assert me_response_after_logout.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token has been revoked" in me_response_after_logout.json()["detail"]

def test_logout_all_user_devices_success(client: TestClient):
    user_email = "logoutall@example.com"
    user_password = "Password123"
    client.post("/auth/register", json={"email": user_email, "name": "Logout All User", "password": user_password})

    token1_data = client.post("/auth/login", data={"username": user_email, "password": user_password}).json()
    token1 = token1_data["access_token"]
    time.sleep(0.01)
    token2_data = client.post("/auth/login", data={"username": user_email, "password": user_password}).json()
    token2 = token2_data["access_token"]

    assert token1 != token2

    decoded1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti1 = decoded1["jti"]
    decoded2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti2 = decoded2["jti"]

    assert is_token_jti_valid(jti1) is True
    assert is_token_jti_valid(jti2) is True

    headers1 = {"Authorization": f"Bearer {token1}"}
    logout_all_response = client.post("/auth/logout-all", headers=headers1)
    assert logout_all_response.status_code == status.HTTP_200_OK
    assert "Logged out from all devices successfully" in logout_all_response.json()["message"]

    assert is_token_jti_valid(jti1) is False
    assert is_token_jti_valid(jti2) is False

    me_response_token1 = client.get("/auth/users/me", headers=headers1)
    assert me_response_token1.status_code == status.HTTP_401_UNAUTHORIZED

    headers2 = {"Authorization": f"Bearer {token2}"}
    me_response_token2 = client.get("/auth/users/me", headers=headers2)
    assert me_response_token2.status_code == status.HTTP_401_UNAUTHORIZED
