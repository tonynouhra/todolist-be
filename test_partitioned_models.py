#!/usr/bin/env python3
"""
Test script to validate the new partitioned models work correctly.
This script tests model imports, relationships, and basic functionality.
"""

import sys
import os
import uuid
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_model_imports():
    """Test that all new models can be imported successfully."""
    print("Testing model imports...")

    try:
        from models.todo_partitioned import (
            TodoActive,
            TodoArchived,
            AITodoInteraction,
            Todo,
        )
        from models.user import User
        from models.project import Project
        from models.file import File

        print("✅ All models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return False


def test_model_creation():
    """Test that model instances can be created."""
    print("Testing model instance creation...")

    try:
        from models.todo_partitioned import TodoActive, TodoArchived, AITodoInteraction

        user_id = uuid.uuid4()

        # Test TodoActive creation
        active_todo = TodoActive(
            user_id=user_id,
            title="Test Active Todo",
            description="Test description",
            status="todo",
            priority=3,
            ai_generated=False,
            depth=0,
        )

        # Test TodoArchived creation
        archived_todo = TodoArchived(
            user_id=user_id,
            title="Test Archived Todo",
            description="Test description",
            status="done",
            priority=2,
            ai_generated=True,
            depth=1,
            archived_at=datetime.now(timezone.utc),
        )

        # Test AITodoInteraction creation
        ai_interaction = AITodoInteraction(
            todo_id=uuid.uuid4(),
            user_id=user_id,
            interaction_type="generate_subtasks",
            prompt="Generate subtasks for this todo",
            response="Generated 3 subtasks",
            subtasks_generated=3,
            model_used="gemini-1.5-flash",
        )

        print("✅ All model instances created successfully")
        return True

    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        return False


def test_model_methods():
    """Test model methods and properties."""
    print("Testing model methods...")

    try:
        from models.todo_partitioned import TodoActive, TodoArchived, Todo

        user_id = uuid.uuid4()

        # Test TodoActive methods
        active_todo = TodoActive(
            user_id=user_id,
            title="Test Active Todo",
            status="todo",
            priority=4,
            due_date=datetime.now(timezone.utc),
            depth=0,
        )

        assert not active_todo.is_completed(), "Active todo should not be completed"
        assert active_todo.can_have_subtasks(), "Active todo should allow subtasks"
        assert active_todo.is_overdue(), "Active todo with past due date should be overdue"

        # Test completed todo
        completed_todo = TodoActive(
            user_id=user_id,
            title="Completed Todo",
            status="done",
            completed_at=datetime.now(timezone.utc),
            depth=0,
        )

        assert completed_todo.is_completed(), "Completed todo should be completed"

        # Test compatibility layer
        compat_todo = Todo.from_active(active_todo)
        assert compat_todo.title == active_todo.title, "Compatibility layer should preserve title"
        assert not compat_todo.is_completed(), "Compatibility todo should match original status"

        print("✅ All model methods work correctly")
        return True

    except Exception as e:
        print(f"❌ Model methods test failed: {e}")
        return False


def test_service_import():
    """Test that the new partitioned service can be imported."""
    print("Testing service import...")

    try:
        from app.domains.todo.service_partitioned import (
            PartitionedTodoService,
            TodoService,
        )

        print("✅ Partitioned services imported successfully")
        return True
    except Exception as e:
        print(f"❌ Service import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting partitioned models test suite...")
    print("=" * 50)

    tests = [
        test_model_imports,
        test_model_creation,
        test_model_methods,
        test_service_import,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
        print()

    print("=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Partitioned models are ready for use")
        return 0
    else:
        print(f"⚠️  Some tests failed: {passed}/{total} passed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
