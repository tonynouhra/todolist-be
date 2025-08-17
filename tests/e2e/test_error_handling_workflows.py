"""
End-to-end functional tests for error handling and edge cases.

This module contains comprehensive end-to-end tests that verify proper
error handling, edge cases, and recovery scenarios in complete workflows.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

from app.exceptions.ai import (
    AIServiceError,
    AIConfigurationError,
    AIQuotaExceededError,
    AITimeoutError
)


class TestErrorHandlingWorkflows:
    """End-to-end tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_authentication_error_workflow(self, client: AsyncClient):
        """Test workflow with various authentication errors."""
        
        # Step 1: Try to access protected endpoints without authentication
        protected_endpoints = [
            ("GET", "/api/auth/me"),
            ("PUT", "/api/auth/me", {"username": "test"}),
            ("POST", "/api/projects/", {"name": "Test Project"}),
            ("GET", "/api/projects/"),
            ("POST", "/api/todos/", {"title": "Test Todo"}),
            ("GET", "/api/todos/"),
            ("POST", "/api/ai/generate-subtasks", {"todo_id": str(uuid.uuid4()), "max_subtasks": 3}),
            ("GET", "/api/ai/status")
        ]
        
        for endpoint_info in protected_endpoints:
            method, endpoint = endpoint_info[0], endpoint_info[1]
            data = endpoint_info[2] if len(endpoint_info) > 2 else None
            
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "POST":
                response = await client.post(endpoint, json=data)
            elif method == "PUT":
                response = await client.put(endpoint, json=data)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Step 2: Try to signup with invalid data
        invalid_signup_cases = [
            {"clerk_user_id": "", "email": "test@example.com", "username": "test"},
            {"clerk_user_id": "valid_id", "email": "invalid_email", "username": "test"},
            {"email": "test@example.com", "username": "test"},  # Missing clerk_user_id
        ]
        
        for invalid_data in invalid_signup_cases:
            response = await client.post("/api/auth/signup", json=invalid_data)
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]
        
        # Step 3: Try duplicate user signup
        valid_user_data = {
            "clerk_user_id": f"clerk_user_{uuid.uuid4()}",
            "email": "duplicate@example.com",
            "username": "duplicateuser"
        }
        
        # First signup should succeed
        first_response = await client.post("/api/auth/signup", json=valid_user_data)
        assert first_response.status_code == status.HTTP_201_CREATED
        
        # Second signup with same clerk_user_id should fail
        second_response = await client.post("/api/auth/signup", json=valid_user_data)
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in second_response.json()["detail"]

    @pytest.mark.asyncio
    async def test_resource_not_found_workflow(self, authenticated_client: AsyncClient):
        """Test workflow with resource not found scenarios."""
        
        fake_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        # Step 1: Try to access non-existent resources
        not_found_endpoints = [
            ("GET", f"/api/projects/{fake_ids[0]}"),
            ("PUT", f"/api/projects/{fake_ids[0]}", {"name": "Updated"}),
            ("DELETE", f"/api/projects/{fake_ids[0]}"),
            ("GET", f"/api/projects/{fake_ids[0]}/todos"),
            ("GET", f"/api/todos/{fake_ids[1]}"),
            ("PUT", f"/api/todos/{fake_ids[1]}", {"title": "Updated"}),
            ("DELETE", f"/api/todos/{fake_ids[1]}"),
            ("PATCH", f"/api/todos/{fake_ids[1]}/toggle-status"),
            ("GET", f"/api/todos/{fake_ids[1]}/subtasks"),
        ]
        
        for endpoint_info in not_found_endpoints:
            method, endpoint = endpoint_info[0], endpoint_info[1]
            data = endpoint_info[2] if len(endpoint_info) > 2 else None
            
            if method == "GET":
                response = await authenticated_client.get(endpoint)
            elif method == "PUT":
                response = await authenticated_client.put(endpoint, json=data)
            elif method == "DELETE":
                response = await authenticated_client.delete(endpoint)
            elif method == "PATCH":
                response = await authenticated_client.patch(endpoint)
            
            # Most endpoints return 200 with error status, some return 404
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
            
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert data["status"] == "error"
                assert "not found" in data["message"].lower()
        
        # Step 2: Try to create todos with non-existent project
        invalid_todo_data = {
            "title": "Invalid Project Todo",
            "project_id": fake_ids[2]
        }
        
        response = await authenticated_client.post("/api/todos/", json=invalid_todo_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Step 3: Try to create subtask with non-existent parent
        invalid_subtask_data = {
            "title": "Orphan Subtask",
            "parent_todo_id": fake_ids[3]
        }
        
        response = await authenticated_client.post("/api/todos/", json=invalid_subtask_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_validation_error_workflow(self, authenticated_client: AsyncClient):
        """Test workflow with various validation errors."""
        
        # Step 1: Test project validation errors
        invalid_project_cases = [
            {"name": ""},  # Empty name
            {"name": "x" * 256},  # Too long name
            {"description": "x" * 10000},  # Too long description (if limit exists)
        ]
        
        for invalid_data in invalid_project_cases:
            response = await authenticated_client.post("/api/projects/", json=invalid_data)
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]
        
        # Step 2: Test todo validation errors
        invalid_todo_cases = [
            {"title": ""},  # Empty title
            {"title": "x" * 501},  # Too long title
            {"priority": 0},  # Invalid priority (too low)
            {"priority": 6},  # Invalid priority (too high)
            {"status": "invalid_status"},  # Invalid status
            {"due_date": "invalid-date-format"},  # Invalid date format
        ]
        
        for invalid_data in invalid_todo_cases:
            response = await authenticated_client.post("/api/todos/", json=invalid_data)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Step 3: Test duplicate project name
        project_data = {"name": "Unique Project Name"}
        first_response = await authenticated_client.post("/api/projects/", json=project_data)
        assert first_response.status_code == status.HTTP_201_CREATED
        
        # Try to create another project with same name
        second_response = await authenticated_client.post("/api/projects/", json=project_data)
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Step 4: Test invalid query parameters
        invalid_query_cases = [
            "/api/todos/?status=invalid_status",
            "/api/todos/?priority=10",
            "/api/todos/?priority=-1",
            "/api/todos/?page=0",
            "/api/todos/?size=0",
            "/api/todos/?size=101",  # Assuming max size is 100
        ]
        
        for endpoint in invalid_query_cases:
            response = await authenticated_client.get(endpoint)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_ai_service_error_workflow(self, authenticated_client: AsyncClient, test_todo):
        """Test workflow with AI service errors."""
        
        ai_request_data = {
            "todo_id": str(test_todo.id),
            "max_subtasks": 3
        }
        
        # Step 1: Test AI configuration error
        with patch('app.domains.ai.service.AIService.generate_subtasks', 
                  side_effect=AIConfigurationError("AI service not configured")):
            response = await authenticated_client.post("/api/ai/generate-subtasks", json=ai_request_data)
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "error"
            assert "AI_CONFIGURATION_ERROR" in data["data"]["error_code"]
            assert isinstance(data["data"]["suggestions"], list)
        
        # Step 2: Test quota exceeded error
        with patch('app.domains.ai.service.AIService.generate_subtasks', 
                  side_effect=AIQuotaExceededError("API quota exceeded")):
            response = await authenticated_client.post("/api/ai/generate-subtasks", json=ai_request_data)
            
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            data = response.json()
            assert data["status"] == "error"
            assert "AI_QUOTA_EXCEEDED" in data["data"]["error_code"]
        
        # Step 3: Test timeout error
        with patch('app.domains.ai.service.AIService.generate_subtasks', 
                  side_effect=AITimeoutError("Request timed out")):
            response = await authenticated_client.post("/api/ai/generate-subtasks", json=ai_request_data)
            
            assert response.status_code == status.HTTP_408_REQUEST_TIMEOUT
            data = response.json()
            assert data["status"] == "error"
            assert "AI_TIMEOUT" in data["data"]["error_code"]
        
        # Step 4: Test generic AI service error
        with patch('app.domains.ai.service.AIService.generate_subtasks', 
                  side_effect=AIServiceError("Generic AI error")):
            response = await authenticated_client.post("/api/ai/generate-subtasks", json=ai_request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["status"] == "error"
            assert "AI_SERVICE_ERROR" in data["data"]["error_code"]
        
        # Step 5: Test AI service status when service is down
        with patch('app.domains.ai.service.AIService.get_service_status', 
                  side_effect=Exception("Service check failed")):
            response = await authenticated_client.get("/api/ai/status")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_available"] is False

    @pytest.mark.asyncio
    async def test_data_consistency_error_workflow(self, authenticated_client: AsyncClient, test_user):
        """Test workflow ensuring data consistency during errors."""
        
        # Step 1: Create project and todos
        project_data = {"name": "Consistency Test Project"}
        project_response = await authenticated_client.post("/api/projects/", json=project_data)
        project_id = project_response.json()["data"]["id"]
        
        todo_data = {
            "title": "Parent Todo",
            "project_id": project_id,
            "status": "todo"
        }
        parent_response = await authenticated_client.post("/api/todos/", json=todo_data)
        parent_todo_id = parent_response.json()["data"]["id"]
        
        # Step 2: Try to create subtask with invalid nesting (simulate deep nesting)
        current_parent_id = parent_todo_id
        
        # Create a chain of todos (test depth limit)
        for i in range(6):  # Assuming max depth is 5
            subtask_data = {
                "title": f"Nested Todo Level {i+1}",
                "parent_todo_id": current_parent_id,
                "project_id": project_id
            }
            
            response = await authenticated_client.post("/api/todos/", json=subtask_data)
            
            if i < 4:  # First 5 levels should succeed
                assert response.status_code == status.HTTP_201_CREATED
                current_parent_id = response.json()["data"]["id"]
            else:  # 6th level should fail
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "depth" in response.json().get("detail", "").lower()
        
        # Step 3: Test transaction rollback scenario
        # Try to update a todo with invalid data after creating subtasks
        
        # First, get the parent with subtasks to verify current state
        parent_with_subtasks_response = await authenticated_client.get(
            f"/api/todos/{parent_todo_id}?include_subtasks=true"
        )
        initial_subtasks_count = len(parent_with_subtasks_response.json()["data"]["subtasks"])
        
        # Try to update parent with invalid project ID
        invalid_update_data = {
            "title": "Updated Parent",
            "project_id": str(uuid.uuid4())  # Non-existent project
        }
        
        update_response = await authenticated_client.put(
            f"/api/todos/{parent_todo_id}", 
            json=invalid_update_data
        )
        assert update_response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Verify that the parent todo wasn't changed and subtasks are still there
        parent_check_response = await authenticated_client.get(
            f"/api/todos/{parent_todo_id}?include_subtasks=true"
        )
        parent_data = parent_check_response.json()["data"]
        assert parent_data["title"] == "Parent Todo"  # Original title
        assert len(parent_data["subtasks"]) == initial_subtasks_count

    @pytest.mark.asyncio
    async def test_concurrent_access_error_workflow(self, authenticated_client: AsyncClient, test_user):
        """Test workflow with simulated concurrent access scenarios."""
        import asyncio
        
        # Step 1: Create a project that will be accessed concurrently
        project_data = {"name": "Concurrent Test Project"}
        project_response = await authenticated_client.post("/api/projects/", json=project_data)
        project_id = project_response.json()["data"]["id"]
        
        # Step 2: Simulate concurrent todo creation
        async def create_todo_with_delay(index):
            await asyncio.sleep(0.01 * index)  # Small delay to simulate timing differences
            todo_data = {
                "title": f"Concurrent Todo {index}",
                "project_id": project_id,
                "priority": (index % 5) + 1
            }
            return await authenticated_client.post("/api/todos/", json=todo_data)
        
        # Create multiple todos concurrently
        concurrent_tasks = [create_todo_with_delay(i) for i in range(10)]
        responses = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify that most operations succeeded despite concurrency
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) == 10
        
        for response in successful_responses:
            assert response.status_code == status.HTTP_201_CREATED
        
        # Step 3: Test concurrent updates to the same todo
        # Create a todo first
        base_todo_data = {
            "title": "Concurrent Update Test",
            "project_id": project_id,
            "status": "todo",
            "priority": 3
        }
        base_todo_response = await authenticated_client.post("/api/todos/", json=base_todo_data)
        todo_id = base_todo_response.json()["data"]["id"]
        
        # Concurrent updates
        async def update_todo(field, value):
            await asyncio.sleep(0.01)  # Small delay
            update_data = {field: value}
            return await authenticated_client.put(f"/api/todos/{todo_id}", json=update_data)
        
        # Multiple concurrent updates
        update_tasks = [
            update_todo("title", "Updated Title 1"),
            update_todo("priority", 5),
            update_todo("status", "in_progress"),
            update_todo("description", "Concurrent update test description")
        ]
        
        update_responses = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # All updates should succeed
        for response in update_responses:
            if not isinstance(response, Exception):
                assert response.status_code == status.HTTP_200_OK
        
        # Step 4: Verify final state is consistent
        final_todo_response = await authenticated_client.get(f"/api/todos/{todo_id}")
        final_todo = final_todo_response.json()["data"]
        
        # The final state should be consistent (one of the concurrent updates should have won)
        assert final_todo["id"] == todo_id
        assert final_todo["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_resource_cleanup_error_workflow(self, authenticated_client: AsyncClient):
        """Test proper resource cleanup during error scenarios."""
        
        # Step 1: Create resources that will need cleanup
        project_data = {"name": "Cleanup Test Project"}
        project_response = await authenticated_client.post("/api/projects/", json=project_data)
        project_id = project_response.json()["data"]["id"]
        
        # Create parent todo
        parent_data = {
            "title": "Cleanup Parent Todo",
            "project_id": project_id
        }
        parent_response = await authenticated_client.post("/api/todos/", json=parent_data)
        parent_id = parent_response.json()["data"]["id"]
        
        # Create subtasks
        subtask_ids = []
        for i in range(3):
            subtask_data = {
                "title": f"Cleanup Subtask {i}",
                "parent_todo_id": parent_id,
                "project_id": project_id
            }
            subtask_response = await authenticated_client.post("/api/todos/", json=subtask_data)
            subtask_ids.append(subtask_response.json()["data"]["id"])
        
        # Step 2: Delete parent todo and verify cascade deletion
        delete_response = await authenticated_client.delete(f"/api/todos/{parent_id}")
        assert delete_response.status_code == status.HTTP_200_OK
        
        # Verify parent is deleted
        parent_check = await authenticated_client.get(f"/api/todos/{parent_id}")
        assert parent_check.json()["status"] == "error"
        
        # Verify subtasks are also deleted (cascade)
        for subtask_id in subtask_ids:
            subtask_check = await authenticated_client.get(f"/api/todos/{subtask_id}")
            assert subtask_check.json()["status"] == "error"
        
        # Step 3: Delete project and verify todos are unassigned (not deleted)
        # Create new todos in the project first
        remaining_todo_ids = []
        for i in range(2):
            todo_data = {
                "title": f"Remaining Todo {i}",
                "project_id": project_id
            }
            todo_response = await authenticated_client.post("/api/todos/", json=todo_data)
            remaining_todo_ids.append(todo_response.json()["data"]["id"])
        
        # Delete project
        project_delete_response = await authenticated_client.delete(f"/api/projects/{project_id}")
        assert project_delete_response.status_code == status.HTTP_200_OK
        
        # Verify project is deleted
        project_check = await authenticated_client.get(f"/api/projects/{project_id}")
        assert project_check.json()["status"] == "error"
        
        # Verify todos still exist but are unassigned from project
        for todo_id in remaining_todo_ids:
            todo_check = await authenticated_client.get(f"/api/todos/{todo_id}")
            assert todo_check.status_code == status.HTTP_200_OK
            todo_data = todo_check.json()["data"]
            assert todo_data["project_id"] is None  # Unassigned from deleted project
        
        # Step 4: Verify statistics are updated correctly after cleanup
        stats_response = await authenticated_client.get("/api/todos/stats/summary")
        stats = stats_response.json()["data"]
        
        # Should reflect the actual remaining todos
        assert stats["total_todos"] >= 2  # At least the 2 remaining todos


