import pytest
from unittest.mock import patch, MagicMock
import uuid

from app.services.project_service import ProjectService
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel
from app.db.models.project_model_db import Project as ProjectDBModel
from app.db.models.task_model_db import Task as TaskDBModel # For cascade delete test
from app.models.project_models import ProjectCreate
from mongoengine.errors import ValidationError

pytestmark = [pytest.mark.unit, pytest.mark.services, pytest.mark.projects]

@pytest.fixture
def project_service_instance() -> ProjectService:
    return ProjectService()

@pytest.fixture
def mock_user_project_creator() -> UserDBModel:
    return UserDBModel(id=uuid.uuid4(), email="projectcreator@example.com")

@pytest.fixture
def mock_ws_for_project() -> WorkspaceDBModel:
    return WorkspaceDBModel(id=uuid.uuid4(), name="Project's Workspace")

@pytest.fixture
def mock_project_create_data() -> ProjectCreate:
    return ProjectCreate(name="Unit Test Project", description="Desc")

# === Test for create_project ===
@patch('app.services.project_service.WorkspaceDBModel.objects')
@patch('app.services.project_service.ProjectDBModel.save') # Mock instance save
def test_create_project_success(mock_project_save, mock_ws_objects, project_service_instance: ProjectService, mock_user_project_creator: UserDBModel, mock_ws_for_project: WorkspaceDBModel, mock_project_create_data: ProjectCreate):
    mock_ws_objects.return_value.first.return_value = mock_ws_for_project # Workspace exists

    with patch('app.services.project_service.ProjectDBModel') as MockedProjectDBModel:
        mock_project_instance = MockedProjectDBModel.return_value
        mock_project_instance.save = mock_project_save # Use the correctly scoped mock for save

        result = project_service_instance.create_project(
            user_db=mock_user_project_creator,
            workspace_id=mock_ws_for_project.id,
            project_data=mock_project_create_data
        )
        MockedProjectDBModel.assert_called_once_with(
            name=mock_project_create_data.name,
            description=mock_project_create_data.description,
            emoji=mock_project_create_data.emoji, # Ensure emoji is handled
            workspace=mock_ws_for_project,
            created_by=mock_user_project_creator
        )
        mock_project_instance.save.assert_called_once()
        assert result == mock_project_instance

@patch('app.services.project_service.WorkspaceDBModel.objects')
def test_create_project_workspace_not_found(mock_ws_objects, project_service_instance: ProjectService, mock_user_project_creator: UserDBModel, mock_project_create_data: ProjectCreate):
    mock_ws_objects.return_value.first.return_value = None # Workspace does not exist
    with pytest.raises(ValueError, match=f"Workspace with ID .* not found."):
        project_service_instance.create_project(
            user_db=mock_user_project_creator,
            workspace_id=uuid.uuid4(), # Some random ID
            project_data=mock_project_create_data
        )

# === Test for delete_project ===
@patch('app.services.project_service.TaskDBModel.objects') # To mock task deletion
@patch('app.services.project_service.ProjectDBModel.objects')
def test_delete_project_success_cascades_tasks(mock_project_objects, mock_task_objects, project_service_instance: ProjectService, mock_user_project_creator: UserDBModel, mock_ws_for_project: WorkspaceDBModel):
    mock_project_instance = MagicMock(spec=ProjectDBModel)
    mock_project_instance.id = uuid.uuid4()
    # Simulate ProjectDBModel.objects(id=..., workspace=...).first()
    mock_project_objects.return_value.first.return_value = mock_project_instance

    # Simulate TaskDBModel.objects(project=mock_project_instance).delete()
    mock_task_queryset = MagicMock() # This is the queryset object
    mock_task_objects.return_value = mock_task_queryset # .objects(project=...) returns the queryset
    # mock_task_queryset.delete = MagicMock() # .delete() is a method on the queryset

    result = project_service_instance.delete_project(
        project_id=mock_project_instance.id,
        workspace_id=mock_ws_for_project.id, # Used to scope the project lookup
        performing_user=mock_user_project_creator
    )
    assert result is True
    mock_project_objects.return_value.first.assert_called_once_with(id=mock_project_instance.id, workspace=mock_ws_for_project.id)
    mock_task_objects.assert_called_with(project=mock_project_instance) # Check the filter argument
    mock_task_queryset.delete.assert_called_once() # Check that delete() was called on the queryset
    mock_project_instance.delete.assert_called_once()
