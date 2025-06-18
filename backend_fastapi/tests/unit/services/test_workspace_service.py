import pytest
from unittest.mock import patch, MagicMock
import uuid

from app.services.workspace_service import WorkspaceService
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.member_model_db import Member as MemberDBModel
from app.db.models.project_model_db import Project as ProjectDBModel # For cascade delete test
from app.models.workspace_models import WorkspaceCreate
from app.models.role_permission_models import RoleEnum
from mongoengine.errors import NotUniqueError, ValidationError

pytestmark = [pytest.mark.unit, pytest.mark.services, pytest.mark.workspaces]

@pytest.fixture
def workspace_service_instance() -> WorkspaceService:
    return WorkspaceService()

@pytest.fixture
def mock_user() -> UserDBModel:
    return UserDBModel(id=uuid.uuid4(), email="owner@example.com", name="Owner")

@pytest.fixture
def mock_workspace_create_data() -> WorkspaceCreate:
    return WorkspaceCreate(name="New Test WS", description="Test WS Desc")

# === Tests for create_workspace ===
@patch('app.services.workspace_service.member_service.add_member_to_workspace')
@patch('app.services.workspace_service.WorkspaceDBModel.save') # Mock instance save
def test_create_workspace_success(mock_ws_save, mock_add_member, workspace_service_instance: WorkspaceService, mock_user: UserDBModel, mock_workspace_create_data: WorkspaceCreate):
    # Mock the WorkspaceDBModel constructor if it's called by service
    with patch('app.services.workspace_service.WorkspaceDBModel') as MockedWorkspaceDBModel:
        mock_ws_instance = MockedWorkspaceDBModel.return_value
        mock_ws_instance.id = uuid.uuid4() # Ensure it has an ID for member service
        mock_ws_instance.save = mock_ws_save # Attach the instance save mock

        mock_add_member.return_value = MemberDBModel() # Simulate successful member add

        result = workspace_service_instance.create_workspace(user_db=mock_user, workspace_data=mock_workspace_create_data)

        MockedWorkspaceDBModel.assert_called_once_with(
            name=mock_workspace_create_data.name,
            description=mock_workspace_create_data.description,
            owner=mock_user
        )
        mock_ws_instance.save.assert_called_once()
        mock_add_member.assert_called_once_with(
            user=mock_user,
            workspace=mock_ws_instance,
            role_name=RoleEnum.OWNER.value
        )
        assert result == mock_ws_instance

@patch('app.services.workspace_service.WorkspaceDBModel.save', side_effect=NotUniqueError("Duplicate error"))
def test_create_workspace_duplicate_error(mock_ws_save_err, workspace_service_instance: WorkspaceService, mock_user: UserDBModel, mock_workspace_create_data: WorkspaceCreate):
    with patch('app.services.workspace_service.WorkspaceDBModel') as MockedWorkspaceDBModel:
        # Ensure the save method on the instance (created by constructor) is the one that raises error
        mock_ws_instance = MockedWorkspaceDBModel.return_value
        mock_ws_instance.save = mock_ws_save_err
        with pytest.raises(ValueError, match="Workspace with this name or invite code might already exist."):
            workspace_service_instance.create_workspace(user_db=mock_user, workspace_data=mock_workspace_create_data)


@patch('app.services.workspace_service.WorkspaceDBModel') # Mock constructor
@patch('app.services.workspace_service.member_service.add_member_to_workspace', side_effect=ValueError("Member add failed"))
def test_create_workspace_member_add_fails_rolls_back(mock_add_member_err, MockedWorkspaceDBModel, workspace_service_instance: WorkspaceService, mock_user: UserDBModel, mock_workspace_create_data: WorkspaceCreate):
    mock_ws_instance = MockedWorkspaceDBModel.return_value
    mock_ws_instance.id = uuid.uuid4()
    mock_ws_instance.delete = MagicMock() # Mock the delete method for rollback

    with pytest.raises(ValueError, match="Workspace creation failed: could not add owner as member: Member add failed"):
        workspace_service_instance.create_workspace(user_db=mock_user, workspace_data=mock_workspace_create_data)

    mock_ws_instance.save.assert_called_once() # Workspace was saved initially
    mock_add_member_err.assert_called_once()
    mock_ws_instance.delete.assert_called_once() # Rollback delete was called


# === Tests for delete_workspace ===
@patch('app.services.workspace_service.ProjectDBModel.objects')
@patch('app.services.workspace_service.MemberDBModel.objects')
@patch('app.services.workspace_service.WorkspaceDBModel.objects')
def test_delete_workspace_success_cascades(mock_ws_objects, mock_member_objects, mock_project_objects, workspace_service_instance: WorkspaceService, mock_user: UserDBModel):
    mock_workspace_instance = MagicMock(spec=WorkspaceDBModel)
    mock_workspace_instance.id = uuid.uuid4()
    mock_ws_objects.return_value.first.return_value = mock_workspace_instance

    # Simulate projects being found and deleted
    mock_project_query_result = MagicMock() # This will be the result of ProjectDBModel.objects(workspace=...)
    mock_project_objects.return_value = mock_project_query_result
    mock_project_instance1 = MagicMock(spec=ProjectDBModel)
    mock_project_instance2 = MagicMock(spec=ProjectDBModel)
    # Make the query result iterable and return mock project instances
    mock_project_query_result.__iter__.return_value = [mock_project_instance1, mock_project_instance2]

    # Simulate member entries being found and deleted (delete on queryset)
    mock_member_queryset_delete = MagicMock()
    mock_member_objects.return_value.delete = mock_member_queryset_delete


    result = workspace_service_instance.delete_workspace(workspace_id=mock_workspace_instance.id, performing_user=mock_user)

    assert result is True
    mock_ws_objects.return_value.first.assert_called_once_with(id=mock_workspace_instance.id)

    mock_project_objects.assert_called_with(workspace=mock_workspace_instance) # Check the query filter
    mock_project_instance1.delete.assert_called_once()
    mock_project_instance2.delete.assert_called_once()

    mock_member_objects.assert_called_with(workspace=mock_workspace_instance) # Check the query filter
    mock_member_queryset_delete.assert_called_once() # .delete() called on the queryset

    mock_workspace_instance.delete.assert_called_once()


@patch('app.services.workspace_service.WorkspaceDBModel.objects')
def test_delete_workspace_not_found(mock_ws_objects, workspace_service_instance: WorkspaceService, mock_user: UserDBModel):
    mock_ws_objects.return_value.first.return_value = None # Workspace not found
    result = workspace_service_instance.delete_workspace(workspace_id=uuid.uuid4(), performing_user=mock_user)
    assert result is False
