# TodoList Backend - Comprehensive Testing Guide

This document provides a complete guide to the testing infrastructure for the TodoList backend application.

## 📋 Table of Contents

- [Test Structure](#test-structure)
- [Test Types](#test-types)
- [Quick Start](#quick-start)
- [Test Configuration](#test-configuration)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Writing Tests](#writing-tests)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

## 🏗️ Test Structure

The test suite is organized into four main categories:

```
tests/
├── conftest.py                    # Global test configuration and fixtures
├── factories.py                   # Test data factories
├── unit/                         # Unit tests - Fast, isolated component tests
│   ├── __init__.py
│   ├── test_user_service.py      # User business logic tests
│   ├── test_todo_service.py      # Todo business logic tests
│   ├── test_project_service.py   # Project business logic tests
│   └── test_ai_service.py        # AI service tests with mocking
├── integration/                  # Integration tests - Database and service interactions
│   ├── __init__.py
│   ├── test_database_integration.py    # Database operations and relationships
│   └── test_service_integration.py     # Cross-service integration tests
├── api/                         # API tests - HTTP endpoint testing
│   ├── __init__.py
│   ├── test_user_controller.py   # Authentication and user endpoints
│   ├── test_todo_controller.py   # Todo CRUD endpoints
│   ├── test_project_controller.py # Project management endpoints
│   └── test_ai_controller.py     # AI service endpoints
└── e2e/                         # End-to-end tests - Complete workflows
    ├── __init__.py
    ├── test_user_workflows.py    # Complete user journey tests
    └── test_error_handling_workflows.py # Error scenarios and edge cases
```

## 🧪 Test Types

### Unit Tests (tests/unit/)
- **Purpose**: Test individual components in isolation
- **Speed**: Very fast (< 1 second per test)
- **Scope**: Service layer business logic
- **Dependencies**: Mocked external dependencies
- **Coverage**: Business logic, validation, error handling

### Integration Tests (tests/integration/)
- **Purpose**: Test component interactions and database operations
- **Speed**: Fast (1-5 seconds per test)
- **Scope**: Database models, relationships, service integration
- **Dependencies**: Test database, real database operations
- **Coverage**: Data persistence, cascading operations, constraints

### API Tests (tests/api/)
- **Purpose**: Test HTTP endpoints and API contracts
- **Speed**: Medium (2-10 seconds per test)
- **Scope**: Controllers, request/response validation, authentication
- **Dependencies**: Test database, mocked external services
- **Coverage**: HTTP status codes, response formats, error handling

### End-to-End Tests (tests/e2e/)
- **Purpose**: Test complete user workflows and system behavior
- **Speed**: Slow (10-60 seconds per test)
- **Scope**: Full application stack, realistic user scenarios
- **Dependencies**: Test database, mocked external services
- **Coverage**: User journeys, error recovery, data consistency

## 🚀 Quick Start

### Prerequisites

1. **Database Setup**: Ensure PostgreSQL is running with a test database
2. **Dependencies**: Install test dependencies
3. **Environment**: Configure test environment variables

```bash
# Install dependencies
pip install -r requirements.txt

# Set up test database
createdb test_ai_todo

# Set environment variables (optional - defaults provided)
export TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost/test_ai_todo"
export TESTING=true
```

### Run All Tests

```bash
# Using the test runner script (recommended)
./run_tests.py --all

# Or using pytest directly
pytest
```

### Run Specific Test Types

```bash
# Unit tests only
./run_tests.py --unit

# Integration tests only
./run_tests.py --integration

# API tests only
./run_tests.py --api

# End-to-end tests only
./run_tests.py --e2e
```

## ⚙️ Test Configuration

### Environment Variables

```bash
# Database
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test_db

# Testing flags
TESTING=true

# AI Service (disabled in tests by default)
GEMINI_API_KEY=
AI_ENABLED=false

# Logging
LOG_LEVEL=INFO
```

### pytest.ini Configuration

The project includes comprehensive pytest configuration:

- **Test Discovery**: Automatic test file and function detection
- **Async Support**: Full asyncio test support
- **Markers**: Categorized test execution
- **Coverage**: Code coverage reporting with minimum thresholds
- **Output**: Detailed test results and timing information

### Test Fixtures (conftest.py)

Global fixtures available to all tests:

- `test_db`: Clean database session per test
- `client`: Unauthenticated HTTP client
- `authenticated_client`: Pre-authenticated HTTP client
- `test_user`, `test_user_2`: Sample user accounts
- `test_project`, `test_project_2`: Sample projects
- `test_todo`, `test_todo_with_subtasks`: Sample todos
- `mock_clerk_auth`: Mocked authentication service
- `mock_ai_service`: Mocked AI service

## 🏃‍♂️ Running Tests

### Test Runner Script

The `run_tests.py` script provides convenient commands:

```bash
# All tests with coverage
./run_tests.py --all --verbose

# Unit tests without coverage
./run_tests.py --unit --no-coverage

# Specific test file
./run_tests.py --specific tests/unit/test_user_service.py

# Tests by marker
./run_tests.py --marker slow

# Check dependencies
./run_tests.py --check-deps
```

### Direct pytest Commands

```bash
# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_user_service.py

# Run specific test method
pytest tests/unit/test_user_service.py::TestUserService::test_create_user_success

# Run tests by marker
pytest -m "unit"
pytest -m "integration"
pytest -m "api"
pytest -m "e2e"

# Parallel execution (if pytest-xdist is installed)
pytest -n 4
```

### Test Markers

Tests are categorized with markers for selective execution:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.api`: API tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.ai`: AI service tests
- `@pytest.mark.auth`: Authentication tests
- `@pytest.mark.database`: Database-specific tests

## 📊 Test Coverage

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View HTML report
open htmlcov/index.html

# Terminal coverage report
pytest --cov=app --cov-report=term-missing
```

### Coverage Targets

- **Overall**: Minimum 80% code coverage
- **Critical paths**: 95%+ coverage for authentication, data validation
- **Service layer**: 90%+ coverage for business logic
- **Controllers**: 85%+ coverage for API endpoints

### Excluded from Coverage

- Migration files
- Configuration files
- External service integrations (tested via mocking)

## ✍️ Writing Tests

### Test Structure

```python
import pytest
from unittest.mock import patch, AsyncMock

class TestFeatureName:
    """Test cases for FeatureName."""

    @pytest.mark.asyncio
    async def test_feature_success(self, test_db, test_user):
        """Test successful feature operation."""
        # Arrange
        service = FeatureService(test_db)
        
        # Act
        result = await service.feature_method(test_user.id)
        
        # Assert
        assert result is not None
        assert result.property == expected_value

    @pytest.mark.asyncio
    async def test_feature_error_handling(self, test_db):
        """Test feature error handling."""
        service = FeatureService(test_db)
        
        with pytest.raises(ExpectedError):
            await service.feature_method(invalid_input)
```

### Best Practices

1. **Test Names**: Descriptive names indicating scenario and expected outcome
2. **Arrange-Act-Assert**: Clear test structure
3. **One Assertion Per Test**: Focus on single behavior
4. **Test Data**: Use factories and fixtures for consistent test data
5. **Mocking**: Mock external dependencies, test real business logic
6. **Async/Await**: Proper async test handling
7. **Error Cases**: Test both success and failure scenarios

### Fixtures Usage

```python
@pytest.mark.asyncio
async def test_with_authenticated_user(authenticated_client, test_project):
    """Test using pre-configured fixtures."""
    response = await authenticated_client.post("/api/todos/", json={
        "title": "Test Todo",
        "project_id": str(test_project.id)
    })
    assert response.status_code == 201
```

### Mocking External Services

```python
@pytest.mark.asyncio
async def test_ai_integration(authenticated_client, test_todo, mock_ai_service):
    """Test with mocked AI service."""
    mock_response = SubtaskGenerationResponse(...)
    
    with patch('app.domains.ai.service.AIService.generate_subtasks', 
               return_value=mock_response):
        response = await authenticated_client.post("/api/ai/generate-subtasks", 
                                                 json={"todo_id": str(test_todo.id)})
        assert response.status_code == 201
```

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_ai_todo
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run tests
      env:
        TEST_DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/test_ai_todo
      run: ./run_tests.py --all --verbose
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: ./run_tests.py --unit --integration
        language: system
        pass_filenames: false
        always_run: true
```

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check if PostgreSQL is running
pg_isready

# Create test database
createdb test_ai_todo

# Reset test database
dropdb test_ai_todo && createdb test_ai_todo
```

#### Import Errors
```bash
# Add project root to Python path
export PYTHONPATH=/path/to/todolist-be:$PYTHONPATH

# Install in development mode
pip install -e .
```

#### Async Test Issues
```python
# Ensure proper async test decoration
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

#### Fixture Scope Issues
```python
# Use appropriate fixture scope
@pytest.fixture(scope="session")  # Expensive setup
@pytest.fixture(scope="function")  # Default, clean per test
@pytest.fixture(scope="module")   # Shared within module
```

### Test Performance

#### Slow Tests
```bash
# Identify slow tests
pytest --durations=10

# Run only fast tests
pytest -m "not slow"

# Parallel execution
pytest -n auto
```

#### Memory Issues
```bash
# Run with memory monitoring
pytest --memray

# Garbage collection between tests
pytest --forked
```

### Debugging Tests

```bash
# Run with debugging
pytest -s --pdb

# Print statements in tests
pytest -s

# Specific test with verbose output
pytest -vv tests/unit/test_user_service.py::TestUserService::test_create_user_success
```

## 📈 Test Metrics

### Current Test Statistics

- **Total Tests**: 150+ comprehensive tests
- **Unit Tests**: 50+ tests covering all service methods
- **Integration Tests**: 30+ tests for database operations
- **API Tests**: 40+ tests for all endpoints
- **E2E Tests**: 20+ tests for complete workflows
- **Coverage**: 85%+ overall code coverage
- **Performance**: Average test suite runtime < 5 minutes

### Quality Gates

- All tests must pass before merge
- Minimum 80% code coverage maintained
- No critical security vulnerabilities
- Performance regression detection
- Integration with external services verified

---

## 🎯 Summary

This comprehensive testing infrastructure ensures:

- **Reliability**: Thorough coverage of all application layers
- **Maintainability**: Clear test organization and documentation  
- **Performance**: Fast feedback with efficient test execution
- **Quality**: High confidence in code changes and deployments
- **Developer Experience**: Easy-to-use tools and clear guidelines

The testing suite provides confidence in the TodoList application's functionality, performance, and reliability across all supported use cases and edge conditions.






















































