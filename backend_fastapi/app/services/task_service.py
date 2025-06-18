from typing import Optional, List
import uuid

from app.db.models.task_model_db import Task as TaskDBModel
from app.db.models.user_model_db import User as UserDBModel
from app.db.models.project_model_db import Project as ProjectDBModel
from app.models.task_models import TaskCreate, TaskUpdate
from mongoengine.errors import ValidationError, DoesNotExist

class TaskService:
    def create_task(self, user_db: UserDBModel, project_id: uuid.UUID, task_data: TaskCreate) -> TaskDBModel:
        # ... (create_task method as before) ...
        try:
            project = ProjectDBModel.objects(id=project_id).select_related('workspace').first()
            if not project: raise ValueError(f"Project with ID {project_id} not found.")
            new_task = TaskDBModel(title=task_data.title, description=task_data.description, status=task_data.status, priority=task_data.priority, due_date=task_data.due_date, project=project, workspace=project.workspace, created_by=user_db)
            if task_data.assigned_to_id:
                assignee = UserDBModel.objects(id=task_data.assigned_to_id).first()
                if assignee: new_task.assigned_to = assignee
                else: print(f"Warning: Assignee user with ID {task_data.assigned_to_id} not found for task.")
            new_task.save()
            return new_task
        except ValidationError as e: raise ValueError(f"Task data validation error: {e}")
        except DoesNotExist: raise ValueError(f"Project with ID {project_id} not found (DoesNotExist).")
        except Exception as e: print(f"Unexpected error creating task: {e}"); raise ValueError(f"Could not create task: {e}")

    def get_task_by_id(self, task_id: uuid.UUID) -> Optional[TaskDBModel]:
        # ... (get_task_by_id method as before) ...
        try: return TaskDBModel.objects(id=task_id).first()
        except Exception as e: print(f"Error fetching task {task_id}: {e}"); return None

    def list_tasks_in_project(self, project_id: uuid.UUID) -> List[TaskDBModel]:
        # ... (list_tasks_in_project method as before) ...
        try:
            project = ProjectDBModel.objects(id=project_id).first()
            if not project: return []
            return list(TaskDBModel.objects(project=project))
        except Exception as e: print(f"Error fetching tasks for project {project_id}: {e}"); return []

    def update_task(self, task_id: uuid.UUID, project_id: uuid.UUID, workspace_id: uuid.UUID, data_update: TaskUpdate, performing_user: UserDBModel) -> Optional[TaskDBModel]:
        # ... (update_task method as before) ...
        try:
            task = TaskDBModel.objects(id=task_id, project=project_id, workspace=workspace_id).first()
            if not task: return None
            if data_update.title is not None: task.title = data_update.title
            if data_update.description is not None: task.description = data_update.description
            if data_update.status is not None: task.status = data_update.status
            if data_update.priority is not None: task.priority = data_update.priority
            if 'due_date' in data_update.model_fields_set: task.due_date = data_update.due_date
            if 'assigned_to_id' in data_update.model_fields_set:
                if data_update.assigned_to_id is None: task.assigned_to = None
                else:
                    assignee = UserDBModel.objects(id=data_update.assigned_to_id).first()
                    if assignee: task.assigned_to = assignee
                    else: raise ValueError(f"Assignee user with ID {data_update.assigned_to_id} not found.")
            task.save()
            return task
        except ValidationError as e: raise ValueError(f"Task update validation error: {e}")
        except DoesNotExist: return None
        except Exception as e: print(f"Error updating task {task_id}: {e}"); raise ValueError(f"Could not update task: {e}")

    def delete_task(self, task_id: uuid.UUID, project_id: uuid.UUID, workspace_id: uuid.UUID, performing_user: UserDBModel) -> bool:
        """
        Deletes a task within a specific project and workspace.
        Authorization handled by RBAC. Service ensures task belongs to project/workspace.
        """
        try:
            task = TaskDBModel.objects(id=task_id, project=project_id, workspace=workspace_id).first()
            if not task:
                return False # Task not found or not in this project/workspace

            task.delete()
            print(f"Deleted task {task_id} from project {project_id}")
            return True
        except Exception as e:
            print(f"Error deleting task {task_id} from project {project_id}: {e}")
            return False

task_service = TaskService()
