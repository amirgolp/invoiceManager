import pytest
from unittest.mock import patch, MagicMock
import uuid

from app.services.task_service import TaskService
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.project_model_db import Project as ProjectDBModel
from app.db.models.workspace_model_db import Workspace as WorkspaceDBModel # For project.workspace
from app.db.models.task_model_db import Task as TaskDBModel
from app.models.task_models import TaskCreate, TaskStatusEnum, TaskPriorityEnum
from mongoengine.errors import ValidationError

pytestmark = [pytest.mark.unit, pytest.mark.services, pytest.mark.tasks]

@pytest.fixture
def task_service_instance() -> TaskService:
    return TaskService()

@pytest.fixture
def mock_user_task_creator() -> UserDBModel:
    return UserDBModel(id=uuid.uuid4(), email="taskcreator@example.com")

@pytest.fixture
def mock_project_for_task(mock_user_task_creator: UserDBModel) -> ProjectDBModel: # Needs a workspace
    workspace = WorkspaceDBModel(id=uuid.uuid4(), name="Task's WS")
    return ProjectDBModel(id=uuid.uuid4(), name="Task's Project", workspace=workspace, created_by=mock_user_task_creator)

@pytest.fixture
def mock_task_create_data() -> TaskCreate:
    return TaskCreate(title="Unit Test Task")

# === Test for create_task ===
@patch('app.services.task_service.ProjectDBModel.objects')
@patch('app.services.task_service.UserDBModel.objects') # For assignee lookup
@patch('app.services.task_service.TaskDBModel.save') # Mock instance save
def test_create_task_success(mock_task_save, mock_user_objects, mock_project_objects, task_service_instance: TaskService, mock_user_task_creator: UserDBModel, mock_project_for_task: ProjectDBModel, mock_task_create_data: TaskCreate):
    mock_project_objects.return_value.select_related.return_value.first.return_value = mock_project_for_task
    # No assignee for this simple case
    mock_user_objects.return_value.first.return_value = None

    with patch('app.services.task_service.TaskDBModel') as MockedTaskDBModel:
        mock_task_instance = MockedTaskDBModel.return_value
        # mock_task_instance.save = mock_task_save # This was an issue, save is on instance, not class
        mock_task_instance.save = MagicMock()


        result = task_service_instance.create_task(
            user_db=mock_user_task_creator,
            project_id=mock_project_for_task.id,
            task_data=mock_task_create_data
        )

        MockedTaskDBModel.assert_called_once_with(
            title=mock_task_create_data.title,
            description=mock_task_create_data.description,
            status=mock_task_create_data.status,
            priority=mock_task_create_data.priority,
            due_date=mock_task_create_data.due_date,
            project=mock_project_for_task,
            workspace=mock_project_for_task.workspace, # Derived
            created_by=mock_user_task_creator,
            assigned_to=None # Since no assignee_id in mock_task_create_data by default
        )
        mock_task_instance.save.assert_called_once()
        assert result == mock_task_instance

@patch('app.services.task_service.ProjectDBModel.objects')
def test_create_task_project_not_found(mock_project_objects, task_service_instance: TaskService, mock_user_task_creator: UserDBModel, mock_task_create_data: TaskCreate):
    mock_project_objects.return_value.select_related.return_value.first.return_value = None # Project not found
    with pytest.raises(ValueError, match=f"Project with ID .* not found."):
        task_service_instance.create_task(
            user_db=mock_user_task_creator,
            project_id=uuid.uuid4(),
            task_data=mock_task_create_data
        )
