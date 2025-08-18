#!/bin/bash

# Script to set up database partitioning for TodoList
# This applies the partitioning strategy for production-scale data

set -e

echo "📊 Setting up database partitioning..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if containers are running
if ! docker-compose ps | grep -q "todolist_postgres.*Up"; then
    print_error "PostgreSQL container is not running. Start with: docker-compose up -d"
    exit 1
fi

# Apply partitioning SQL files in order
SCALING_DIR="migrations/scaling"

if [ ! -d "$SCALING_DIR" ]; then
    print_error "Scaling directory not found: $SCALING_DIR"
    exit 1
fi

echo "🔄 Applying partitioning scripts..."

# 1. Create partitioned tables
if [ -f "$SCALING_DIR/001_create_partitioned_tables.sql" ]; then
    echo "Creating partitioned tables..."
    if docker-compose exec -T postgres psql -U todouser -d ai_todo < "$SCALING_DIR/001_create_partitioned_tables.sql"; then
        print_status "Partitioned tables created"
    else
        print_error "Failed to create partitioned tables"
        exit 1
    fi
else
    print_warning "001_create_partitioned_tables.sql not found"
fi

# 2. Migrate existing data
if [ -f "$SCALING_DIR/002_migrate_existing_data.sql" ]; then
    echo "Migrating existing data..."
    if docker-compose exec -T postgres psql -U todouser -d ai_todo < "$SCALING_DIR/002_migrate_existing_data.sql"; then
        print_status "Data migration completed"
    else
        print_warning "Data migration failed (might be normal if no existing data)"
    fi
else
    print_warning "002_migrate_existing_data.sql not found"
fi

# 3. Create maintenance jobs
if [ -f "$SCALING_DIR/003_create_maintenance_jobs.sql" ]; then
    echo "Setting up maintenance jobs..."
    if docker-compose exec -T postgres psql -U todouser -d ai_todo < "$SCALING_DIR/003_create_maintenance_jobs.sql"; then
        print_status "Maintenance jobs created"
    else
        print_warning "Maintenance jobs setup failed"
    fi
else
    print_warning "003_create_maintenance_jobs.sql not found"
fi

# 4. Apply indexing optimizations
if [ -f "$SCALING_DIR/005_indexing_optimization.sql" ]; then
    echo "Applying indexing optimizations..."
    if docker-compose exec -T postgres psql -U todouser -d ai_todo < "$SCALING_DIR/005_indexing_optimization.sql"; then
        print_status "Indexing optimizations applied"
    else
        print_warning "Indexing optimizations failed"
    fi
else
    print_warning "005_indexing_optimization.sql not found"
fi

# 5. Update application models (Python file)
if [ -f "$SCALING_DIR/004_update_application_models.py" ]; then
    echo "Updating application models..."
    if docker-compose exec -T backend python "$SCALING_DIR/004_update_application_models.py"; then
        print_status "Application models updated"
    else
        print_warning "Application models update failed"
    fi
else
    print_warning "004_update_application_models.py not found"
fi

# Verify partitioning setup
echo "🔍 Verifying partitioning setup..."
PARTITION_CHECK=$(docker-compose exec -T postgres psql -U todouser -d ai_todo -t -c "
    SELECT COUNT(*) 
    FROM information_schema.tables 
    WHERE table_name LIKE 'todos_y%' OR table_name LIKE '%_partitioned';
")

if [ "$PARTITION_CHECK" -gt 0 ]; then
    print_status "Partitioning verified - found $PARTITION_CHECK partitioned tables"
else
    print_warning "No partitioned tables found. Partitioning may not be set up correctly."
fi

# Show current partitions
echo "📋 Current partitions:"
docker-compose exec -T postgres psql -U todouser -d ai_todo -c "
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
    FROM pg_tables 
    WHERE tablename LIKE 'todos_y%' 
       OR tablename LIKE '%_partitioned'
    ORDER BY tablename;
"

print_status "Partitioning setup complete!"

echo ""
echo "📝 Next steps:"
echo "   - Monitor partition performance"
echo "   - Set up automated partition maintenance"
echo "   - Update application code to use partitioned tables if needed"