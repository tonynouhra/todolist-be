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

