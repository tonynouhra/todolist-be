#!/bin/bash

# Docker Setup Script for TodoList Backend
# This script sets up the Docker environment and applies migrations

set -e  # Exit on any error

echo "🐳 TodoList Docker Setup Starting..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install Docker Compose."
    exit 1
fi

# Step 1: Setup hosts file (optional)
echo "🌐 Setting up custom domains..."
if [ -f "scripts/setup-hosts.sh" ]; then
    print_warning "To set up custom domains (api.todolist.local), run:"
    echo "    sudo ./scripts/setup-hosts.sh"
    echo ""
else
    print_warning "setup-hosts.sh not found, skipping domain setup"
fi

# Step 2: Environment setup
echo "⚙️  Setting up environment..."
if [ ! -f ".env" ]; then
    if [ -f ".env.docker" ]; then
        cp .env.docker .env
        print_status "Copied .env.docker to .env"
        print_warning "Please edit .env with your actual API keys before continuing"
        echo "Required keys: CLERK_SECRET_KEY, GEMINI_API_KEY, AWS credentials"
        read -p "Press Enter after updating .env file..."
    else
        print_error ".env.docker file not found. Please create environment configuration."
        exit 1
    fi
else
    print_status "Using existing .env file"
fi

# Step 3: Build and start containers
echo "🏗️  Building and starting Docker containers..."
docker-compose down 2>/dev/null || true
docker-compose build
docker-compose up -d

# Step 4: Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
timeout=60
counter=0
until docker-compose exec -T postgres pg_isready -U todouser -d ai_todo >/dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        print_error "Database failed to start within $timeout seconds"
        docker-compose logs postgres
        exit 1
    fi
    echo -n "."
done
echo ""
print_status "Database is ready"

# Step 5: Run Alembic migrations
echo "🔄 Running database migrations..."
if docker-compose exec -T backend alembic upgrade head; then
    print_status "Database migrations completed successfully"
else
    print_warning "Migration failed or no migrations to run. This might be normal for a fresh setup."
    
    # Try to create initial migration if none exist
    echo "🆕 Attempting to create initial migration..."
    if docker-compose exec -T backend alembic revision --autogenerate -m "initial_migration"; then
        print_status "Initial migration created"
        echo "🔄 Running the new migration..."
        if docker-compose exec -T backend alembic upgrade head; then
            print_status "Initial migration applied successfully"
        else
            print_error "Failed to apply initial migration"
        fi
    else
        print_warning "Could not create initial migration. You may need to set this up manually."
    fi
fi

# Step 6: Apply partitioning (if needed)
echo "📊 Checking for partitioning setup..."
if [ -f "migrations/scaling/001_create_partitioned_tables.sql" ]; then
    print_warning "Partitioned tables setup found. Apply manually if needed:"
    echo "    docker-compose exec postgres psql -U todouser -d ai_todo -f /app/migrations/scaling/001_create_partitioned_tables.sql"
else
    print_status "No partitioning setup required"
fi

# Step 7: Check container health
echo "🩺 Checking container health..."
sleep 5

# Check backend health
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    print_status "Backend is healthy (http://localhost:8000)"
else
    print_warning "Backend health check failed on localhost:8000"
fi

# Check custom domain if hosts was set up
if curl -f http://api.todolist.local/health >/dev/null 2>&1; then
    print_status "Custom domain is working (http://api.todolist.local)"
elif [ -f "/etc/hosts" ] && grep -q "api.todolist.local" /etc/hosts; then
    print_warning "Custom domain configured but not responding. Check nginx container."
else
    print_warning "Custom domain not set up. Run: sudo ./scripts/setup-hosts.sh"
fi

# Step 8: Show container status
echo "📋 Container Status:"
docker-compose ps

# Step 9: Show access URLs
echo ""
echo "🌐 Access URLs:"
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check:      http://localhost:8000/health"
echo ""
if grep -q "api.todolist.local" /etc/hosts 2>/dev/null; then
    echo "   Custom Domain API: http://api.todolist.local/docs"
    echo "   Custom Health:     http://api.todolist.local/health"
    echo ""
fi

echo "🎉 Docker setup complete!"
echo ""
echo "📝 Useful commands:"
echo "   View logs:         docker-compose logs -f backend"
echo "   Stop services:     docker-compose down"
echo "   Restart:           docker-compose restart backend"
echo "   Database CLI:      docker-compose exec postgres psql -U todouser -d ai_todo"
echo "   Backend shell:     docker-compose exec backend bash"