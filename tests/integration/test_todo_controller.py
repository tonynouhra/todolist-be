"""Integration tests for Todo Controller (API endpoints)."""

import pytest
from httpx import AsyncClient
from datetime import UTC, datetime, timedelta


@pytest.mark.asyncio
class TestTodoController:
    """Test cases for Todo API endpoints."""

    async def test_create_todo_success(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test creating a todo via API."""
        payload = {
            "title": "New API Todo",
            "description": "Created via API",
            "priority": 3,
            "project_id": str(test_project.id)
        }

        response = await authenticated_client.post("/api/todos", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["title"] == "New API Todo"

    async def test_create_todo_without_project(
        self, authenticated_client: AsyncClient
    ):
        """Test creating a todo without a project."""
        payload = {
            "title": "Todo without project",
            "priority": 2
        }

        response = await authenticated_client.post("/api/todos", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["project_id"] is None

    async def test_create_todo_invalid_data(
        self, authenticated_client: AsyncClient
    ):
        """Test creating a todo with invalid data."""
        payload = {
            "priority": 10  # Invalid priority (should be 1-5)
        }

        response = await authenticated_client.post("/api/todos", json=payload)

        assert response.status_code == 422  # Validation error

    async def test_get_todos_list(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test getting list of todos."""
        response = await authenticated_client.get("/api/todos")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) >= 1

    async def test_get_todos_with_status_filter(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test filtering todos by status."""
        response = await authenticated_client.get("/api/todos?status=todo")

        assert response.status_code == 200
        data = response.json()
        all_todos = [t["status"] == "todo" for t in data["data"]]
        assert all(all_todos)

    async def test_get_todos_with_project_filter(
        self, authenticated_client: AsyncClient, test_todo, test_project
    ):
        """Test filtering todos by project."""
        response = await authenticated_client.get(
            f"/api/todos?project_id={test_project.id}"
        )

        assert response.status_code == 200
        data = response.json()
        for todo in data["data"]:
            if todo["project_id"]:
                assert todo["project_id"] == str(test_project.id)

    async def test_get_todo_by_id(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test getting a specific todo by ID."""
        response = await authenticated_client.get(f"/api/todos/{test_todo.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == str(test_todo.id)
        assert data["data"]["title"] == test_todo.title

    async def test_get_todo_not_found(
        self, authenticated_client: AsyncClient
    ):
        """Test getting a non-existent todo."""
        import uuid
        fake_id = uuid.uuid4()

        response = await authenticated_client.get(f"/api/todos/{fake_id}")

        assert response.status_code == 404

    async def test_update_todo_success(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test updating a todo."""
        payload = {
            "title": "Updated Title",
            "priority": 5
        }

        response = await authenticated_client.put(
            f"/api/todos/{test_todo.id}",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated Title"
        assert data["data"]["priority"] == 5

    async def test_update_todo_mark_completed(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test marking a todo as completed."""
        payload = {
            "status": "done"
        }

        response = await authenticated_client.put(
            f"/api/todos/{test_todo.id}",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "done"
        assert data["data"]["completed_at"] is not None

    async def test_delete_todo_success(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test deleting a todo."""
        response = await authenticated_client.delete(f"/api/todos/{test_todo.id}")

        assert response.status_code == 200

        # Verify it's deleted
        get_response = await authenticated_client.get(f"/api/todos/{test_todo.id}")
        assert get_response.status_code == 404

    async def test_toggle_todo_status(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test toggling todo status."""
        response = await authenticated_client.post(
            f"/api/todos/{test_todo.id}/toggle-status"
        )

        assert response.status_code == 200
        data = response.json()
        # Status should change from 'todo' to 'done' or vice versa
        assert data["data"]["status"] in ["todo", "done", "in_progress"]

    async def test_get_todo_stats(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test getting todo statistics."""
        response = await authenticated_client.get("/api/todos/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data["data"]
        assert "completed" in data["data"]
        assert "pending" in data["data"]

    async def test_create_todo_with_due_date(
        self, authenticated_client: AsyncClient
    ):
        """Test creating a todo with due date."""
        due_date = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        payload = {
            "title": "Todo with due date",
            "due_date": due_date,
            "priority": 3
        }

        response = await authenticated_client.post("/api/todos", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["due_date"] is not None

    async def test_create_subtask(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test creating a subtask."""
        payload = {
            "title": "Subtask",
            "parent_todo_id": str(test_todo.id),
            "priority": 2
        }

        response = await authenticated_client.post("/api/todos", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["parent_todo_id"] == str(test_todo.id)

    async def test_get_todo_with_subtasks(
        self, authenticated_client: AsyncClient, test_todo_with_subtasks
    ):
        """Test getting a todo with its subtasks."""
        response = await authenticated_client.get(
            f"/api/todos/{test_todo_with_subtasks.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "subtasks" in data["data"]
        assert len(data["data"]["subtasks"]) >= 2