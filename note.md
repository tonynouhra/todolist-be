# Start development server
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v

# Run migrations
alembic upgrade head

# Format code
black app/ tests/
isort app/ tests/

# Type checking
mypy app/


alembic revision --autogenerate -m "Description of changes"
alembic upgrade head


curl -X POST "http://localhost:8000/api/projects/" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "My First Project",
      "description": "A sample project for organizing todos"
    }'

  2. Get All Projects (with pagination and search)

  curl -X GET "http://localhost:8000/api/projects/?page=1&size=20" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"

  curl -X GET "http://localhost:8000/api/projects/?search=first&page=1&size=10" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"

  3. Get Project by ID

  curl -X GET "http://localhost:8000/api/projects/550e8400-e29b-41d4-a716-446655440000" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"

  4. Get Project with Todos

  curl -X GET "http://localhost:8000/api/projects/550e8400-e29b-41d4-a716-446655440000?include_todos=true" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"

  5. Update Project

  curl -X PUT "http://localhost:8000/api/projects/550e8400-e29b-41d4-a716-446655440000" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Updated Project Name",
      "description": "Updated project description"
    }'

  6. Delete Project

  curl -X DELETE "http://localhost:8000/api/projects/550e8400-e29b-41d4-a716-446655440000" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"

  7. Get Project Statistics

  curl -X GET "http://localhost:8000/api/projects/stats/summary" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"

  8. Get Project Todos

  curl -X GET "http://localhost:8000/api/projects/550e8400-e29b-41d4-a716-446655440000/todos" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"

