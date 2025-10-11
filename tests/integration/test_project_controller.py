"""Integration tests for Project Controller (API endpoints)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestProjectController:
    """Test cases for Project API endpoints."""

    async def test_create_project_success(
        self, authenticated_client: AsyncClient
    ):
        """Test creating a project via API."""
        payload = {
            "name": "New API Project",
            "description": "Created via API"
        }

        response = await authenticated_client.post("/api/projects", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "New API Project"

    async def test_create_project_duplicate_name(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test creating a project with duplicate name."""
        payload = {
            "name": test_project.name,
            "description": "Duplicate name"
        }

        response = await authenticated_client.post("/api/projects", json=payload)

        assert response.status_code == 400

    async def test_get_projects_list(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test getting list of projects."""
        response = await authenticated_client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) >= 1

    async def test_get_projects_with_search(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test searching projects by name."""
        response = await authenticated_client.get(
            f"/api/projects?search={test_project.name}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert any(p["name"] == test_project.name for p in data["data"])

    async def test_get_project_by_id(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test getting a specific project by ID."""
        response = await authenticated_client.get(f"/api/projects/{test_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == str(test_project.id)
        assert data["data"]["name"] == test_project.name

    async def test_get_project_not_found(
        self, authenticated_client: AsyncClient
    ):
        """Test getting a non-existent project."""
        import uuid
        fake_id = uuid.uuid4()

        response = await authenticated_client.get(f"/api/projects/{fake_id}")

        assert response.status_code == 404

    async def test_update_project_success(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test updating a project."""
        payload = {
            "name": "Updated Project Name",
            "description": "Updated description"
        }

        response = await authenticated_client.put(
            f"/api/projects/{test_project.id}",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Project Name"

    async def test_update_project_duplicate_name(
        self, authenticated_client: AsyncClient, test_project, test_project_2
    ):
        """Test updating project with duplicate name."""
        payload = {
            "name": test_project_2.name
        }

        response = await authenticated_client.put(
            f"/api/projects/{test_project.id}",
            json=payload
        )

        assert response.status_code == 400

    async def test_delete_project_success(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test deleting a project."""
        response = await authenticated_client.delete(f"/api/projects/{test_project.id}")

        assert response.status_code == 200

        # Verify it's deleted
        get_response = await authenticated_client.get(f"/api/projects/{test_project.id}")
        assert get_response.status_code == 404

    async def test_get_project_stats(
        self, authenticated_client: AsyncClient, test_project
    ):
        """Test getting project statistics."""
        response = await authenticated_client.get("/api/projects/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_projects" in data["data"]

    async def test_get_project_with_todo_counts(
        self, authenticated_client: AsyncClient, test_project, test_todo
    ):
        """Test getting project with todo counts."""
        response = await authenticated_client.get(
            f"/api/projects/{test_project.id}/with-counts"
        )

        assert response.status_code == 200
        data = response.json()
        assert "todo_count" in data["data"]