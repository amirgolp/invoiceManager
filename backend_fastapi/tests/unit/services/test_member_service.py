import pytest
from unittest.mock import patch, MagicMock
import uuid

from app.services.member_service import MemberService
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.role_model_db import Role as RoleDBModel
from app.models.role_permission_models import RoleEnum
from mongoengine.errors import DoesNotExist # For simulating not found

# Pytest markers
pytestmark = [pytest.mark.unit, pytest.mark.services, pytest.mark.members]

@pytest.fixture
def member_service_instance() -> MemberService:
    return MemberService()

@pytest.fixture
def mock_user_owner() -> UserDBModel:
    user = UserDBModel(id=uuid.uuid4(), email="owner@example.com", name="Owner User")
    return user

@pytest.fixture
def mock_user_member() -> UserDBModel:
    user = UserDBModel(id=uuid.uuid4(), email="member@example.com", name="Member User")
    return user

@pytest.fixture
def mock_workspace(mock_user_owner: UserDBModel) -> WorkspaceDBModel:
    workspace = WorkspaceDBModel(id=uuid.uuid4(), name="Test Workspace", owner=mock_user_owner)
    return workspace

@pytest.fixture
def mock_role_owner() -> RoleDBModel:
    return RoleDBModel(name=RoleEnum.OWNER.value, permissions=[]) # Permissions not checked by this service method directly

@pytest.fixture
def mock_role_admin() -> RoleDBModel:
    return RoleDBModel(name=RoleEnum.ADMIN.value, permissions=[])

@pytest.fixture
def mock_role_member() -> RoleDBModel:
    return RoleDBModel(name=RoleEnum.MEMBER.value, permissions=[])


# === Tests for add_member_to_workspace ===
@patch('app.services.member_service.RoleDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
@patch('app.services.member_service.MemberDBModel.save') # Mock the save method of the instance
def test_add_member_success(mock_member_save, mock_member_objects, mock_role_objects, member_service_instance: MemberService, mock_user_member: UserDBModel, mock_workspace: WorkspaceDBModel, mock_role_member: RoleDBModel):
    mock_role_objects.return_value.first.return_value = mock_role_member # Role exists
    mock_member_objects.return_value.first.return_value = None # Member does not exist yet

    # We need to mock the MemberDBModel constructor if it's called
    with patch('app.services.member_service.MemberDBModel') as MockedMemberDBModel:
        mock_instance = MockedMemberDBModel.return_value
        mock_instance.save = MagicMock()

        result = member_service_instance.add_member_to_workspace(user=mock_user_member, workspace=mock_workspace, role_name=RoleEnum.MEMBER.value)

        MockedMemberDBModel.assert_called_once_with(user=mock_user_member, workspace=mock_workspace, role_name=RoleEnum.MEMBER.value)
        mock_instance.save.assert_called_once()
        assert result == mock_instance

@patch('app.services.member_service.RoleDBModel.objects')
def test_add_member_invalid_role(mock_role_objects, member_service_instance: MemberService, mock_user_member: UserDBModel, mock_workspace: WorkspaceDBModel):
    mock_role_objects.return_value.first.return_value = None # Role does NOT exist
    with pytest.raises(ValueError, match="Role 'MEMBER' does not exist"):
        member_service_instance.add_member_to_workspace(user=mock_user_member, workspace=mock_workspace, role_name=RoleEnum.MEMBER.value)

@patch('app.services.member_service.RoleDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_add_member_already_exists(mock_member_objects, mock_role_objects, member_service_instance: MemberService, mock_user_member: UserDBModel, mock_workspace: WorkspaceDBModel, mock_role_member: RoleDBModel):
    mock_role_objects.return_value.first.return_value = mock_role_member
    mock_member_objects.return_value.first.return_value = MemberDBModel() # Member already exists

    with pytest.raises(ValueError, match=f"User {mock_user_member.email} is already a member"):
        member_service_instance.add_member_to_workspace(user=mock_user_member, workspace=mock_workspace, role_name=RoleEnum.MEMBER.value)


# === Tests for remove_member_from_workspace ===
@patch('app.services.member_service.WorkspaceDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_remove_member_success(mock_member_objects, mock_workspace_objects, member_service_instance: MemberService, mock_user_owner: UserDBModel, mock_user_member: UserDBModel, mock_workspace: WorkspaceDBModel):
    mock_workspace_objects.return_value.select_related.return_value.first.return_value = mock_workspace

    mock_member_to_remove = MemberDBModel(user=mock_user_member, workspace=mock_workspace, role_name=RoleEnum.MEMBER.value)
    mock_member_objects.return_value.first.return_value = mock_member_to_remove
    mock_member_to_remove.delete = MagicMock() # Mock the delete method of the instance

    result = member_service_instance.remove_member_from_workspace(user_to_remove_id=mock_user_member.id, workspace_id=mock_workspace.id, performing_user=mock_user_owner)
    assert result is True
    mock_member_to_remove.delete.assert_called_once()

@patch('app.services.member_service.WorkspaceDBModel.objects')
def test_remove_member_workspace_not_found(mock_workspace_objects, member_service_instance: MemberService, mock_user_owner: UserDBModel, mock_user_member: UserDBModel):
    mock_workspace_objects.return_value.select_related.return_value.first.return_value = None
    with pytest.raises(ValueError, match="Workspace not found"):
        member_service_instance.remove_member_from_workspace(user_to_remove_id=mock_user_member.id, workspace_id=uuid.uuid4(), performing_user=mock_user_owner)

@patch('app.services.member_service.WorkspaceDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_remove_member_member_not_found(mock_member_objects, mock_workspace_objects, member_service_instance: MemberService, mock_user_owner: UserDBModel, mock_user_member: UserDBModel, mock_workspace: WorkspaceDBModel):
    mock_workspace_objects.return_value.select_related.return_value.first.return_value = mock_workspace
    mock_member_objects.return_value.first.return_value = None # Member not found
    with pytest.raises(ValueError, match="Member not found in this workspace"):
        member_service_instance.remove_member_from_workspace(user_to_remove_id=mock_user_member.id, workspace_id=mock_workspace.id, performing_user=mock_user_owner)

@patch('app.services.member_service.WorkspaceDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_remove_member_cannot_remove_owner(mock_member_objects, mock_workspace_objects, member_service_instance: MemberService, mock_user_owner: UserDBModel, mock_workspace: WorkspaceDBModel):
    # Workspace owner is mock_user_owner. We try to remove mock_user_owner.
    mock_workspace.owner = mock_user_owner # Ensure workspace.owner is set for the test
    mock_workspace_objects.return_value.select_related.return_value.first.return_value = mock_workspace

    # This mock isn't strictly needed for this path, but good for consistency
    mock_member_owner_entry = MemberDBModel(user=mock_user_owner, workspace=mock_workspace, role_name=RoleEnum.OWNER.value)
    mock_member_objects.return_value.first.return_value = mock_member_owner_entry

    with pytest.raises(ValueError, match="Cannot remove the workspace owner"):
        member_service_instance.remove_member_from_workspace(user_to_remove_id=mock_user_owner.id, workspace_id=mock_workspace.id, performing_user=mock_user_owner)


# === Tests for update_member_role ===
@patch('app.services.member_service.RoleDBModel.objects')
@patch('app.services.member_service.WorkspaceDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_update_member_role_success(mock_member_objects, mock_workspace_objects, mock_role_objects, member_service_instance: MemberService, mock_user_owner: UserDBModel, mock_user_member: UserDBModel, mock_workspace: WorkspaceDBModel, mock_role_admin: RoleDBModel):
    mock_workspace_objects.return_value.select_related.return_value.first.return_value = mock_workspace

    mock_member_to_update = MemberDBModel(user=mock_user_member, workspace=mock_workspace, role_name=RoleEnum.MEMBER.value)
    mock_member_to_update.save = MagicMock() # Mock save on the instance
    mock_member_objects.return_value.first.return_value = mock_member_to_update

    mock_role_objects.return_value.first.return_value = mock_role_admin # New role 'ADMIN' exists

    result = member_service_instance.update_member_role(user_to_update_id=mock_user_member.id, workspace_id=mock_workspace.id, new_role_name=RoleEnum.ADMIN.value, performing_user=mock_user_owner)

    assert result == mock_member_to_update
    assert result.role_name == RoleEnum.ADMIN.value
    mock_member_to_update.save.assert_called_once()


@patch('app.services.member_service.RoleDBModel.objects')
@patch('app.services.member_service.WorkspaceDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_update_member_role_cannot_demote_sole_owner(mock_member_objects, mock_workspace_objects, mock_role_objects, member_service_instance: MemberService, mock_user_owner: UserDBModel, mock_workspace: WorkspaceDBModel, mock_role_admin: RoleDBModel):
    mock_workspace.owner = mock_user_owner # mock_user_owner is the owner
    mock_workspace_objects.return_value.select_related.return_value.first.return_value = mock_workspace

    mock_member_owner_entry = MemberDBModel(user=mock_user_owner, workspace=mock_workspace, role_name=RoleEnum.OWNER.value)
    mock_member_objects.return_value.first.return_value = mock_member_owner_entry # This is the member being updated

    mock_role_objects.return_value.first.return_value = mock_role_admin # Target role 'ADMIN' exists

    # Mock the count for other owners
    mock_member_objects.return_value.count.return_value = 0 # No other owners

    with pytest.raises(ValueError, match="Cannot change the role of the sole owner to a non-owner role"):
        member_service_instance.update_member_role(user_to_update_id=mock_user_owner.id, workspace_id=mock_workspace.id, new_role_name=RoleEnum.ADMIN.value, performing_user=mock_user_owner)

@patch('app.services.member_service.RoleDBModel.objects')
@patch('app.services.member_service.WorkspaceDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_update_member_role_new_role_not_found(mock_member_objects, mock_workspace_objects, mock_role_objects, member_service_instance: MemberService, mock_user_owner: UserDBModel, mock_user_member: UserDBModel, mock_workspace: WorkspaceDBModel):
    mock_workspace_objects.return_value.select_related.return_value.first.return_value = mock_workspace
    mock_member_entry = MemberDBModel(user=mock_user_member, workspace=mock_workspace, role_name=RoleEnum.MEMBER.value)
    mock_member_objects.return_value.first.return_value = mock_member_entry

    mock_role_objects.return_value.first.return_value = None # New role does NOT exist

    with pytest.raises(ValueError, match="Role 'NON_EXISTENT_ROLE' does not exist"):
        member_service_instance.update_member_role(user_to_update_id=mock_user_member.id, workspace_id=mock_workspace.id, new_role_name="NON_EXISTENT_ROLE", performing_user=mock_user_owner)

# TODO: Add tests for list_members_in_workspace (simpler, mostly checks DB query)


# === Tests for list_members_in_workspace ===
@patch('app.services.member_service.WorkspaceDBModel.objects')
@patch('app.services.member_service.MemberDBModel.objects')
def test_list_members_in_workspace_success(mock_member_objects, mock_workspace_objects, member_service_instance: MemberService, mock_workspace: WorkspaceDBModel):
    mock_workspace_objects.return_value.first.return_value = mock_workspace # Workspace exists
    mock_member_list = [MemberDBModel(), MemberDBModel()] # Simulate two members found
    mock_member_objects.return_value.select_related.return_value = mock_member_list

    result = member_service_instance.list_members_in_workspace(workspace_id=mock_workspace.id)

    assert result == mock_member_list
    mock_workspace_objects.return_value.first.assert_called_once_with(id=mock_workspace.id)
    # To check the filter part of the query: mock_member_objects.assert_any_call(workspace=mock_workspace.id)
    # The actual call is on the queryset from MemberDBModel.objects(workspace=workspace_id)
    # So, we check that MemberDBModel.objects was called with the workspace_id
    mock_member_objects.assert_called_with(workspace=mock_workspace.id)
    mock_member_objects.return_value.select_related.assert_called_once_with('user')

@patch('app.services.member_service.WorkspaceDBModel.objects')
def test_list_members_in_workspace_not_found(mock_workspace_objects, member_service_instance: MemberService):
    mock_workspace_objects.return_value.first.return_value = None # Workspace does NOT exist
    ws_id = uuid.uuid4()
    result = member_service_instance.list_members_in_workspace(workspace_id=ws_id)
    assert result == []
    mock_workspace_objects.return_value.first.assert_called_once_with(id=ws_id)
