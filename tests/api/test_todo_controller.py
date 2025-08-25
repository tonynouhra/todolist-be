"""
API tests for Todo controller.

This module contains comprehensive API endpoint tests for the todo controller,
testing all CRUD operations, filtering, pagination, and hierarchical features.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status


class TestTodoController:
    """Test cases for Todo API endpoints."""

    @pytest.mark.asyncio
    async def test_create_todo_success(self, authenticated_client: AsyncClient, test_project):
        """Test successful todo creation."""
        todo_data = {
            "title": "New Todo",
            "description": "A new test todo",
            "status": "todo",
            "priority": 4,
            "project_id": str(test_project.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }

        response = await authenticated_client.post("/api/todos/", json=todo_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Todo created successfully"
        assert data["data"]["title"] == "New Todo"
        assert data["data"]["priority"] == 4

    @pytest.mark.asyncio
    async def test_create_todo_minimal(self, authenticated_client: AsyncClient):
        """Test creating todo with minimal required data."""
        todo_data = {"title": "Minimal Todo"}

        response = await authenticated_client.post("/api/todos/", json=todo_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["title"] == "Minimal Todo"
        assert data["data"]["status"] == "todo"
        assert data["data"]["priority"] == 3  # Default priority

    @pytest.mark.asyncio
    async def test_create_todo_with_subtask_generation(self, authenticated_client: AsyncClient):
        """Test creating todo with AI subtask generation."""
        todo_data = {
            "title": "AI Enhanced Todo",
            "description": "This should generate subtasks",
            "generate_ai_subtasks": True,
        }

        with patch("app.domains.todo.service.TodoService._generate_ai_subtasks"):
            response = await authenticated_client.post("/api/todos/", json=todo_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["data"]["title"] == "AI Enhanced Todo"

    @pytest.mark.asyncio
    async def test_create_subtask(self, authenticated_client: AsyncClient, test_todo):
        """Test creating a subtask."""
        subtask_data = {
            "title": "Subtask",
            "parent_todo_id": str(test_todo.id),
            "priority": 2,
        }

        response = await authenticated_client.post("/api/todos/", json=subtask_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["title"] == "Subtask"
        assert data["data"]["parent_todo_id"] == str(test_todo.id)

    @pytest.mark.asyncio
    async def test_create_todo_invalid_project(self, authenticated_client: AsyncClient):
        """Test creating todo with invalid project ID."""
        fake_project_id = str(uuid.uuid4())
        todo_data = {"title": "Invalid Project Todo", "project_id": fake_project_id}

        response = await authenticated_client.post("/api/todos/", json=todo_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_todo_missing_title(self, authenticated_client: AsyncClient):
        """Test creating todo without required title."""
        todo_data = {"description": "Missing title"}

        response = await authenticated_client.post("/api/todos/", json=todo_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_todo_unauthorized(self, client: AsyncClient):
        """Test creating todo without authentication."""
        todo_data = {"title": "Unauthorized Todo"}

        response = await client.post("/api/todos/", json=todo_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_todos_list_basic(self, authenticated_client: AsyncClient):
        """Test getting basic todos list."""
        # Create some test todos first
        for i in range(3):
            todo_data = {"title": f"Test Todo {i}"}
            await authenticated_client.post("/api/todos/", json=todo_data)

        response = await authenticated_client.get("/api/todos/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 3
        assert len(data["todos"]) >= 3

    @pytest.mark.asyncio
    async def test_get_todos_list_with_status_filter(self, authenticated_client: AsyncClient):
        """Test todos list with status filter."""
        # Create todos with different statuses
        await authenticated_client.post(
            "/api/todos/", json={"title": "Todo Item", "status": "todo"}
        )
        await authenticated_client.post(
            "/api/todos/", json={"title": "Done Item", "status": "done"}
        )

        response = await authenticated_client.get("/api/todos/?status=done")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for todo in data["todos"]:
            assert todo["status"] == "done"

    @pytest.mark.asyncio
    async def test_get_todos_list_with_priority_filter(self, authenticated_client: AsyncClient):
        """Test todos list with priority filter."""
        await authenticated_client.post(
            "/api/todos/", json={"title": "High Priority", "priority": 5}
        )
        await authenticated_client.post(
            "/api/todos/", json={"title": "Low Priority", "priority": 1}
        )

        response = await authenticated_client.get("/api/todos/?priority=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for todo in data["todos"]:
            assert todo["priority"] == 5

    @pytest.mark.asyncio
    async def test_get_todos_list_with_project_filter(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test todos list with project filter."""
        await authenticated_client.post(
            "/api/todos/",
            json={"title": "Project Todo", "project_id": str(test_project.id)},
        )

        response = await authenticated_client.get(f"/api/todos/?project_id={test_project.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for todo in data["todos"]:
            assert todo["project_id"] == str(test_project.id)

    @pytest.mark.asyncio
    async def test_get_todos_list_with_search(self, authenticated_client: AsyncClient):
        """Test todos list with search filter."""
        await authenticated_client.post(
            "/api/todos/",
            json={
                "title": "Important Meeting",
                "description": "Discuss quarterly results",
            },
        )
        await authenticated_client.post(
            "/api/todos/",
            json={"title": "Code Review", "description": "Review pull requests"},
        )

        response = await authenticated_client.get("/api/todos/?search=meeting")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any("Meeting" in todo["title"] for todo in data["todos"])

    @pytest.mark.asyncio
    async def test_get_todos_list_pagination(self, authenticated_client: AsyncClient):
        """Test todos list pagination."""
        # Create multiple todos
        for i in range(15):
            await authenticated_client.post("/api/todos/", json={"title": f"Page Todo {i}"})

        # Test first page
        response = await authenticated_client.get("/api/todos/?page=1&size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10
        assert len(data["todos"]) == 10
        assert data["has_next"] is True

    @pytest.mark.asyncio
    async def test_get_todos_list_invalid_status(self, authenticated_client: AsyncClient):
        """Test todos list with invalid status filter."""
        response = await authenticated_client.get("/api/todos/?status=invalid_status")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_todo_by_id_success(self, authenticated_client: AsyncClient, test_todo):
        """Test getting todo by ID."""
        response = await authenticated_client.get(f"/api/todos/{test_todo.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == str(test_todo.id)
        assert data["data"]["title"] == test_todo.title

    @pytest.mark.asyncio
    async def test_get_todo_by_id_with_subtasks(
        self, authenticated_client: AsyncClient, test_todo_with_subtasks
    ):
        """Test getting todo with its subtasks."""
        response = await authenticated_client.get(
            f"/api/todos/{test_todo_with_subtasks.id}?include_subtasks=true"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "subtasks" in data["data"]
        assert len(data["data"]["subtasks"]) == 2

    @pytest.mark.asyncio
    async def test_get_todo_by_id_nonexistent(self, authenticated_client: AsyncClient):
        """Test getting non-existent todo."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(f"/api/todos/{fake_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Todo not found"

    @pytest.mark.asyncio
    async def test_get_todo_by_id_invalid_uuid(self, authenticated_client: AsyncClient):
        """Test getting todo with invalid UUID."""
        response = await authenticated_client.get("/api/todos/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_todo_success(self, authenticated_client: AsyncClient, test_todo):
        """Test successful todo update."""
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "status": "in_progress",
            "priority": 5,
        }

        response = await authenticated_client.put(f"/api/todos/{test_todo.id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["title"] == "Updated Title"
        assert data["data"]["status"] == "in_progress"
        assert data["data"]["priority"] == 5

    @pytest.mark.asyncio
    async def test_update_todo_partial(self, authenticated_client: AsyncClient, test_todo):
        """Test partial todo update."""
        original_description = test_todo.description
        update_data = {"title": "New Title Only"}

        response = await authenticated_client.put(f"/api/todos/{test_todo.id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["title"] == "New Title Only"
        assert data["data"]["description"] == original_description

    @pytest.mark.asyncio
    async def test_update_todo_nonexistent(self, authenticated_client: AsyncClient):
        """Test updating non-existent todo."""
        fake_id = str(uuid.uuid4())
        update_data = {"title": "Should Fail"}

        response = await authenticated_client.put(f"/api/todos/{fake_id}", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_todo_success(self, authenticated_client: AsyncClient, test_todo):
        """Test successful todo deletion."""
        todo_id = str(test_todo.id)

        response = await authenticated_client.delete(f"/api/todos/{todo_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Todo deleted successfully"

        # Verify todo is deleted
        get_response = await authenticated_client.get(f"/api/todos/{todo_id}")
        get_data = get_response.json()
        assert get_data["status"] == "error"

    @pytest.mark.asyncio
    async def test_delete_todo_with_subtasks(
        self, authenticated_client: AsyncClient, test_todo_with_subtasks
    ):
        """Test deleting todo that has subtasks."""
        parent_id = str(test_todo_with_subtasks.id)
        subtask_ids = [str(subtask.id) for subtask in test_todo_with_subtasks.subtasks]

        response = await authenticated_client.delete(f"/api/todos/{parent_id}")

        assert response.status_code == status.HTTP_200_OK

        # Verify parent and subtasks are deleted
        for subtask_id in subtask_ids:
            get_response = await authenticated_client.get(f"/api/todos/{subtask_id}")
            get_data = get_response.json()
            assert get_data["status"] == "error"

    @pytest.mark.asyncio
    async def test_delete_todo_nonexistent(self, authenticated_client: AsyncClient):
        """Test deleting non-existent todo."""
        fake_id = str(uuid.uuid4())

        response = await authenticated_client.delete(f"/api/todos/{fake_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Failed to delete todo"

    @pytest.mark.asyncio
    async def test_toggle_todo_status_to_done(self, authenticated_client: AsyncClient, test_todo):
        """Test toggling todo status to done."""
        response = await authenticated_client.patch(f"/api/todos/{test_todo.id}/toggle-status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_toggle_todo_status_to_todo(
        self, authenticated_client: AsyncClient, completed_todo
    ):
        """Test toggling completed todo status back to todo."""
        response = await authenticated_client.patch(f"/api/todos/{completed_todo.id}/toggle-status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["status"] == "todo"

    @pytest.mark.asyncio
    async def test_get_todo_stats(self, authenticated_client: AsyncClient):
        """Test getting todo statistics."""
        # Create todos with different statuses
        await authenticated_client.post("/api/todos/", json={"title": "Pending", "status": "todo"})
        await authenticated_client.post(
            "/api/todos/", json={"title": "In Progress", "status": "in_progress"}
        )
        await authenticated_client.post(
            "/api/todos/", json={"title": "Completed", "status": "done"}
        )

        response = await authenticated_client.get("/api/todos/stats/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "total_todos" in data["data"]
        assert "completed_todos" in data["data"]
        assert "completion_rate" in data["data"]

    @pytest.mark.asyncio
    async def test_get_todo_subtasks(
        self, authenticated_client: AsyncClient, test_todo_with_subtasks
    ):
        """Test getting subtasks of a todo."""
        response = await authenticated_client.get(
            f"/api/todos/{test_todo_with_subtasks.id}/subtasks"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert len(data["todos"]) == 2

        # Verify all returned items are subtasks of the parent
        for subtask in data["todos"]:
            assert subtask["parent_todo_id"] == str(test_todo_with_subtasks.id)

    @pytest.mark.asyncio
    async def test_get_todo_subtasks_nonexistent_parent(self, authenticated_client: AsyncClient):
        """Test getting subtasks of non-existent parent todo."""
        fake_id = str(uuid.uuid4())

        response = await authenticated_client.get(f"/api/todos/{fake_id}/subtasks")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["todos"]) == 0

    @pytest.mark.asyncio
    async def test_get_todo_subtasks_pagination(self, authenticated_client: AsyncClient, test_todo):
        """Test subtasks pagination."""
        # Create multiple subtasks
        for i in range(15):
            await authenticated_client.post(
                "/api/todos/",
                json={"title": f"Subtask {i}", "parent_todo_id": str(test_todo.id)},
            )

        response = await authenticated_client.get(
            f"/api/todos/{test_todo.id}/subtasks?page=1&size=10"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10
        assert len(data["todos"]) == 10
        assert data["has_next"] is True

    @pytest.mark.asyncio
    async def test_todos_unauthorized_access(self, client: AsyncClient, test_todo):
        """Test accessing todos endpoints without authentication."""
        endpoints = [
            ("GET", "/api/todos/"),
            ("GET", f"/api/todos/{test_todo.id}"),
            ("PUT", f"/api/todos/{test_todo.id}"),
            ("DELETE", f"/api/todos/{test_todo.id}"),
            ("PATCH", f"/api/todos/{test_todo.id}/toggle-status"),
            ("GET", "/api/todos/stats/summary"),
            ("GET", f"/api/todos/{test_todo.id}/subtasks"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "PUT":
                response = await client.put(endpoint, json={"title": "test"})
            elif method == "DELETE":
                response = await client.delete(endpoint)
            elif method == "PATCH":
                response = await client.patch(endpoint)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_todo_validation_comprehensive(self, authenticated_client: AsyncClient):
        """Test comprehensive validation for todo creation."""
        invalid_cases = [
            # Title too long (assuming 500 char limit)
            {"title": "x" * 501},
            # Invalid status
            {"title": "Valid Title", "status": "invalid_status"},
            # Invalid priority
            {"title": "Valid Title", "priority": 6},  # Assuming 1-5 scale
            {"title": "Valid Title", "priority": 0},
            # Invalid due date format
            {"title": "Valid Title", "due_date": "invalid-date"},
        ]

        for invalid_data in invalid_cases:
            response = await authenticated_client.post("/api/todos/", json=invalid_data)
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
            ]
