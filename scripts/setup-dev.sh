#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up TodoList Backend Development Environment"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "🔨 Installing development dependencies..."
pip install \
    pytest-cov \
    black \
    isort \
    ruff \
    mypy \
    bandit \
    safety \
    pre-commit \
    pip-audit

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Set up environment variables
echo "🌍 Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || cat > .env << EOF
# Development environment variables
DEBUG=true
TESTING=false

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/ai_todo_dev
TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost/test_ai_todo

# Authentication
CLERK_SECRET_KEY=your_clerk_secret_key_here

# AI Service
GEMINI_API_KEY=your_gemini_api_key_here
AI_ENABLED=true

# File Storage
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET_NAME=your_s3_bucket

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your_super_secret_key_here
EOF
    echo "📝 Created .env file. Please update with your actual values."
fi

# Check database connection
echo "🗄️ Checking database connection..."
if ! command -v psql &> /dev/null; then
    echo "⚠️ PostgreSQL client not found. Please install PostgreSQL."
    echo "   macOS: brew install postgresql"
    echo "   Ubuntu: sudo apt-get install postgresql-client"
else
    echo "✅ PostgreSQL client found"
fi

# Check Redis connection
echo "📮 Checking Redis connection..."
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️ Redis client not found. Please install Redis."
    echo "   macOS: brew install redis"
    echo "   Ubuntu: sudo apt-get install redis-server"
else
    echo "✅ Redis client found"
fi

# Run initial tests
echo "🧪 Running initial tests..."
if python run_tests.py --unit --no-coverage; then
    echo "✅ Initial tests passed"
else
    echo "⚠️ Some tests failed. This might be due to missing database setup."
fi

# Setup complete
echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Update .env file with your configuration"
echo "   2. Set up your PostgreSQL database"
echo "   3. Run 'alembic upgrade head' to set up database schema"
echo "   4. Start development server: 'uvicorn app.main:app --reload'"
echo ""
echo "🔧 Useful commands:"
echo "   - Run tests: python run_tests.py --all"
echo "   - Format code: black app/ tests/ && isort app/ tests/"
echo "   - Lint code: ruff check app/ tests/"
echo "   - Security check: bandit -r app/"
echo "   - Type check: mypy app/"
echo ""
echo "📚 Documentation:"
echo "   - Project docs: docs/"
echo "   - API docs: http://localhost:8000/docs (when server is running)"