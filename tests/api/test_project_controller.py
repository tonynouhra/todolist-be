"""
API tests for Project controller.

This module contains comprehensive API endpoint tests for the project controller,
testing all CRUD operations, project-todo relationships, and statistics.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient


class TestProjectController:
    """Test cases for Project API endpoints."""

    @pytest.mark.asyncio
    async def test_create_project_success(self, authenticated_client: AsyncClient):
        """Test successful project creation."""
        project_data = {"name": "New Project", "description": "A new test project"}

        response = await authenticated_client.post("/api/projects/", json=project_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Project created successfully"
        assert data["data"]["name"] == "New Project"
        assert data["data"]["description"] == "A new test project"

    @pytest.mark.asyncio
    async def test_create_project_minimal(self, authenticated_client: AsyncClient):
        """Test creating project with minimal required data."""
        project_data = {"name": "Minimal Project"}

        response = await authenticated_client.post("/api/projects/", json=project_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["name"] == "Minimal Project"
        assert data["data"]["description"] is None

    @pytest.mark.asyncio
    async def test_create_project_duplicate_name(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test creating project with duplicate name."""
        project_data = {
            "name": test_project.name,
            "description": "Different description",
        }

        response = await authenticated_client.post("/api/projects/", json=project_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_project_missing_name(self, authenticated_client: AsyncClient):
        """Test creating project without required name."""
        project_data = {"description": "Missing name"}

        response = await authenticated_client.post("/api/projects/", json=project_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_project_unauthorized(self, client: AsyncClient):
        """Test creating project without authentication."""
        project_data = {"name": "Unauthorized Project"}

        response = await client.post("/api/projects/", json=project_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_projects_list_basic(self, authenticated_client: AsyncClient):
        """Test getting basic projects list."""
        # Create test projects
        for i in range(3):
            project_data = {"name": f"Test Project {i}"}
            await authenticated_client.post("/api/projects/", json=project_data)

        response = await authenticated_client.get("/api/projects/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 3
        assert len(data["projects"]) >= 3

    @pytest.mark.asyncio
    async def test_get_projects_list_with_search(self, authenticated_client: AsyncClient):
        """Test projects list with search filter."""
        await authenticated_client.post(
            "/api/projects/",
            json={"name": "Important Project", "description": "Very important work"},
        )
        await authenticated_client.post(
            "/api/projects/",
            json={"name": "Regular Project", "description": "Regular work"},
        )

        response = await authenticated_client.get("/api/projects/?search=important")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any("Important" in project["name"] for project in data["projects"])

    @pytest.mark.asyncio
    async def test_get_projects_list_pagination(self, authenticated_client: AsyncClient):
        """Test projects list pagination."""
        # Create multiple projects
        for i in range(15):
            await authenticated_client.post("/api/projects/", json={"name": f"Page Project {i}"})

        # Test first page
        response = await authenticated_client.get("/api/projects/?page=1&size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10
        assert len(data["projects"]) == 10
        assert data["has_next"] is True

    @pytest.mark.asyncio
    async def test_get_projects_list_with_todo_counts(self, authenticated_client: AsyncClient):
        """Test that projects list includes todo counts."""
        # Create project
        project_response = await authenticated_client.post(
            "/api/projects/", json={"name": "Project with Todos"}
        )
        project_id = project_response.json()["data"]["id"]

        # Add some todos to the project
        for i in range(3):
            await authenticated_client.post(
                "/api/todos/",
                json={
                    "title": f"Project Todo {i}",
                    "project_id": project_id,
                    "status": "done" if i == 0 else "todo",
                },
            )

        response = await authenticated_client.get("/api/projects/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Find our project in the results
        project = next(p for p in data["projects"] if p["id"] == project_id)
        assert project["todo_count"] == 3
        assert project["completed_todo_count"] == 1

    @pytest.mark.asyncio
    async def test_get_project_by_id_success(self, authenticated_client: AsyncClient, test_project):
        """Test getting project by ID."""
        response = await authenticated_client.get(f"/api/projects/{test_project.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == str(test_project.id)
        assert data["data"]["name"] == test_project.name

    @pytest.mark.asyncio
    async def test_get_project_by_id_with_todos(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test getting project with its todos."""
        # Add some todos to the project
        for i in range(2):
            await authenticated_client.post(
                "/api/todos/",
                json={"title": f"Project Todo {i}", "project_id": str(test_project.id)},
            )

        response = await authenticated_client.get(
            f"/api/projects/{test_project.id}?include_todos=true"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "todos" in data["data"]
        assert len(data["data"]["todos"]) == 2

    @pytest.mark.asyncio
    async def test_get_project_by_id_nonexistent(self, authenticated_client: AsyncClient):
        """Test getting non-existent project."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(f"/api/projects/{fake_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Project not found"

    @pytest.mark.asyncio
    async def test_get_project_by_id_invalid_uuid(self, authenticated_client: AsyncClient):
        """Test getting project with invalid UUID."""
        response = await authenticated_client.get("/api/projects/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_project_success(self, authenticated_client: AsyncClient, test_project):
        """Test successful project update."""
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description",
        }

        response = await authenticated_client.put(
            f"/api/projects/{test_project.id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "Updated Project Name"
        assert data["data"]["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_project_partial(self, authenticated_client: AsyncClient, test_project):
        """Test partial project update."""
        original_description = test_project.description
        update_data = {"name": "New Name Only"}

        response = await authenticated_client.put(
            f"/api/projects/{test_project.id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["name"] == "New Name Only"
        assert data["data"]["description"] == original_description

    @pytest.mark.asyncio
    async def test_update_project_duplicate_name(
        self, authenticated_client: AsyncClient, test_project, test_project_2
    ):
        """Test updating project to have duplicate name."""
        update_data = {"name": test_project_2.name}

        response = await authenticated_client.put(
            f"/api/projects/{test_project.id}", json=update_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_project_same_name(self, authenticated_client: AsyncClient, test_project):
        """Test updating project with same name (should succeed)."""
        update_data = {
            "name": test_project.name,
            "description": "Updated description only",
        }

        response = await authenticated_client.put(
            f"/api/projects/{test_project.id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["name"] == test_project.name
        assert data["data"]["description"] == "Updated description only"

    @pytest.mark.asyncio
    async def test_update_project_nonexistent(self, authenticated_client: AsyncClient):
        """Test updating non-existent project."""
        fake_id = str(uuid.uuid4())
        update_data = {"name": "Should Fail"}

        response = await authenticated_client.put(f"/api/projects/{fake_id}", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_project_success(self, authenticated_client: AsyncClient, test_project):
        """Test successful project deletion."""
        project_id = str(test_project.id)

        response = await authenticated_client.delete(f"/api/projects/{project_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Project deleted successfully"

        # Verify project is deleted
        get_response = await authenticated_client.get(f"/api/projects/{project_id}")
        get_data = get_response.json()
        assert get_data["status"] == "error"

    @pytest.mark.asyncio
    async def test_delete_project_with_todos(self, authenticated_client: AsyncClient, test_project):
        """Test deleting project that has todos (should unassign them)."""
        # Add todos to the project
        todo_responses = []
        for i in range(3):
            todo_response = await authenticated_client.post(
                "/api/todos/",
                json={"title": f"Project Todo {i}", "project_id": str(test_project.id)},
            )
            todo_responses.append(todo_response)

        project_id = str(test_project.id)
        response = await authenticated_client.delete(f"/api/projects/{project_id}")

        assert response.status_code == status.HTTP_200_OK

        # Verify todos still exist but are unassigned from project
        for todo_response in todo_responses:
            todo_id = todo_response.json()["data"]["id"]
            get_todo_response = await authenticated_client.get(f"/api/todos/{todo_id}")
            get_todo_data = get_todo_response.json()
            assert get_todo_data["status"] == "success"
            assert get_todo_data["data"]["project_id"] is None

    @pytest.mark.asyncio
    async def test_delete_project_nonexistent(self, authenticated_client: AsyncClient):
        """Test deleting non-existent project."""
        fake_id = str(uuid.uuid4())

        response = await authenticated_client.delete(f"/api/projects/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Project not found"
        assert data["error_code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_project_stats(self, authenticated_client: AsyncClient):
        """Test getting project statistics."""
        # Create projects with and without todos
        project1_response = await authenticated_client.post(
            "/api/projects/", json={"name": "Project with todos"}
        )
        project1_id = project1_response.json()["data"]["id"]

        await authenticated_client.post("/api/projects/", json={"name": "Empty project"})

        # Add todos to first project
        for i in range(3):
            await authenticated_client.post(
                "/api/todos/", json={"title": f"Todo {i}", "project_id": project1_id}
            )

        response = await authenticated_client.get("/api/projects/stats/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "total_projects" in data["data"]
        assert "projects_with_todos" in data["data"]
        assert "average_todos_per_project" in data["data"]

        stats = data["data"]
        assert stats["total_projects"] >= 2
        assert stats["projects_with_todos"] >= 1

    @pytest.mark.asyncio
    async def test_get_project_todos(self, authenticated_client: AsyncClient, test_project):
        """Test getting all todos for a project."""
        # Add todos to the project
        todo_ids = []
        for i in range(3):
            todo_response = await authenticated_client.post(
                "/api/todos/",
                json={"title": f"Project Todo {i}", "project_id": str(test_project.id)},
            )
            todo_ids.append(todo_response.json()["data"]["id"])

        response = await authenticated_client.get(f"/api/projects/{test_project.id}/todos")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "project" in data["data"]
        assert "todos" in data["data"]
        assert len(data["data"]["todos"]) == 3

        # Verify all todos belong to this project
        for todo in data["data"]["todos"]:
            assert todo["project_id"] == str(test_project.id)
            assert todo["id"] in todo_ids

    @pytest.mark.asyncio
    async def test_get_project_todos_nonexistent_project(self, authenticated_client: AsyncClient):
        """Test getting todos for non-existent project."""
        fake_id = str(uuid.uuid4())

        response = await authenticated_client.get(f"/api/projects/{fake_id}/todos")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Project not found"

    @pytest.mark.asyncio
    async def test_get_project_todos_empty_project(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test getting todos for project with no todos."""
        response = await authenticated_client.get(f"/api/projects/{test_project.id}/todos")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["todos"]) == 0

    @pytest.mark.asyncio
    async def test_projects_unauthorized_access(self, client: AsyncClient, test_project):
        """Test accessing project endpoints without authentication."""
        endpoints = [
            ("GET", "/api/projects/"),
            ("GET", f"/api/projects/{test_project.id}"),
            ("PUT", f"/api/projects/{test_project.id}"),
            ("DELETE", f"/api/projects/{test_project.id}"),
            ("GET", "/api/projects/stats/summary"),
            ("GET", f"/api/projects/{test_project.id}/todos"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "PUT":
                response = await client.put(endpoint, json={"name": "test"})
            elif method == "DELETE":
                response = await client.delete(endpoint)

            assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_project_user_isolation(
        self, authenticated_client: AsyncClient, client: AsyncClient, test_user_2
    ):
        """Test that users can only access their own projects."""
        # Create project with first user
        project_response = await authenticated_client.post(
            "/api/projects/", json={"name": "Private Project"}
        )
        project_id = project_response.json()["data"]["id"]

        # Try to access with second user
        def override_get_current_user_2():
            return test_user_2

        from app.core.dependencies import get_current_user
        from app.database import get_db
        from app.main import app

        # Create authenticated client for second user
        app.dependency_overrides[get_current_user] = override_get_current_user_2
        from httpx import AsyncClient

        async with AsyncClient(app=app, base_url="http://test") as second_user_client:
            response = await second_user_client.get(f"/api/projects/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "Project not found"

        # Clean up overrides
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_project_validation_comprehensive(self, authenticated_client: AsyncClient):
        """Test comprehensive validation for project creation."""
        invalid_cases = [
            # Name too long (assuming 255 char limit)
            {"name": "x" * 256},
            # Empty name
            {"name": ""},
            {"name": "   "},  # Only whitespace
        ]

        for invalid_data in invalid_cases:
            response = await authenticated_client.post("/api/projects/", json=invalid_data)
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
            ]

    @pytest.mark.asyncio
    async def test_project_ordering(self, authenticated_client: AsyncClient):
        """Test that projects are returned in correct order (newest first)."""
        # Create projects with known names
        project_names = ["First Project", "Second Project", "Third Project"]

        for name in project_names:
            await authenticated_client.post("/api/projects/", json={"name": name})
            # Small delay to ensure different timestamps
            import asyncio

            await asyncio.sleep(0.01)

        response = await authenticated_client.get("/api/projects/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should be ordered by updated_at descending (newest first)
        project_names_returned = [p["name"] for p in data["projects"] if p["name"] in project_names]
        assert project_names_returned == [
            "Third Project",
            "Second Project",
            "First Project",
        ]
