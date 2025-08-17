# Database Scaling Implementation Guide

## 🚀 Quick Start Guide

This guide walks you through implementing the hybrid database scaling solution for your AI Todo List application.

## 📋 Prerequisites

- PostgreSQL 12+ with partitioning support
- Python 3.11+ with SQLAlchemy 2.0
- Administrative database access
- Backup of existing data (CRITICAL!)

## 🗂️ Files Overview

| File | Purpose | When to Run |
|------|---------|-------------|
| `001_create_partitioned_tables.sql` | Create new partitioned table structure | Phase 1 |
| `002_migrate_existing_data.sql` | Migrate data from old to new tables | Phase 2 |
| `003_create_maintenance_jobs.sql` | Set up automated maintenance | Phase 3 |
| `004_update_application_models.py` | Updated SQLAlchemy models | Phase 4 |
| `005_indexing_optimization.sql` | Create optimized indexes | Phase 5 |

## ⚡ Step-by-Step Implementation

### Phase 1: Create Infrastructure (30 minutes)

1. **Backup your database:**
```bash
pg_dump -h localhost -U your_user -d your_database > backup_before_scaling.sql
```

2. **Run the partitioning script:**
```bash
psql -h localhost -U your_user -d your_database -f migrations/scaling/001_create_partitioned_tables.sql
```

3. **Verify partitions were created:**
```sql
SELECT tablename, tableowner FROM pg_tables WHERE tablename LIKE 'todos_active%';
```

**Expected Result:** 16 active partitions + 4 archive partitions

### Phase 2: Migrate Data (1-4 hours depending on data size)

1. **Check data statistics:**
```sql
SELECT count(*) as total_todos FROM todos;
SELECT count(*) as completed_todos FROM todos WHERE status = 'done';
```

2. **Run migration script:**
```bash
psql -h localhost -U your_user -d your_database -f migrations/scaling/002_migrate_existing_data.sql
```

3. **Monitor progress:**
```sql
SELECT * FROM migration_progress ORDER BY start_time DESC;
```

4. **Validate migration:**
```sql
SELECT * FROM validate_migration();
```

**Expected Result:** All validation checks should return 'PASS'

### Phase 3: Set Up Maintenance (15 minutes)

1. **Create maintenance jobs:**
```bash
psql -h localhost -U your_user -d your_database -f migrations/scaling/003_create_maintenance_jobs.sql
```

2. **Test maintenance functions:**
```sql
SELECT * FROM run_daily_maintenance();
```

3. **Schedule maintenance (optional - using cron):**
```bash
# Add to crontab
0 2 * * * psql -h localhost -U your_user -d your_database -c "SELECT run_daily_maintenance();"
0 3 * * 0 psql -h localhost -U your_user -d your_database -c "SELECT run_weekly_maintenance();"
```

### Phase 4: Update Application Code (2-4 hours)

1. **Update your models:**
   - Copy code from `004_update_application_models.py`
   - Replace existing `Todo` model with `TodoActive` and `TodoArchived`
   - Update relationships in `User` and `Project` models

2. **Update service layer:**
```python
# Example service updates
class TodoService:
    async def get_user_todos(self, user_id: UUID, include_archived: bool = False):
        if include_archived:
            # Query both active and archived tables
            active = await self.db.execute(
                select(TodoActive).where(TodoActive.user_id == user_id)
            )
            archived = await self.db.execute(
                select(TodoArchived).where(TodoArchived.user_id == user_id)
            )
            return list(active.scalars().all()) + list(archived.scalars().all())
        else:
            # Query only active table
            result = await self.db.execute(
                select(TodoActive).where(TodoActive.user_id == user_id)
            )
            return result.scalars().all()
```

3. **Update imports:**
```python
# Replace
from models.todo import Todo

# With
from models.todo_partitioned import TodoActive, TodoArchived, AITodoInteraction
```

### Phase 5: Optimize Performance (30 minutes)

1. **Create indexes:**
```bash
psql -h localhost -U your_user -d your_database -f migrations/scaling/005_indexing_optimization.sql
```

2. **Monitor index creation:**
```sql
SELECT 
    schemaname, tablename, indexname, indexdef
FROM pg_indexes 
WHERE tablename LIKE 'todos_active%'
ORDER BY tablename, indexname;
```

3. **Test query performance:**
```sql
EXPLAIN ANALYZE 
SELECT * FROM todos_active 
WHERE user_id = 'your-test-user-id' 
ORDER BY priority DESC, created_at DESC;
```

## 🧪 Testing Strategy

### 1. Functional Testing

```python
# Test script example
import pytest
from app.domains.todo.service import TodoService

async def test_partitioned_todos():
    # Create todo in active partition
    todo = await service.create_todo(todo_data, user_id)
    assert todo.id is not None
    
    # Verify it's in active table
    active_todos = await service.get_user_todos(user_id, include_archived=False)
    assert len(active_todos) == 1
    
    # Complete and archive todo
    await service.complete_todo(todo.id, user_id)
    await archive_completed_todos(0)  # Archive immediately for testing
    
    # Verify it moved to archive
    archived_todos = await service.get_user_todos(user_id, include_archived=True)
    assert any(t.id == todo.id for t in archived_todos)
```

### 2. Performance Testing

```sql
-- Test with different user loads
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM todos_active 
WHERE user_id = $1 AND status = 'todo' 
ORDER BY priority DESC 
LIMIT 20;

-- Should show: Index Scan using idx_todos_active_user_status_priority
-- Execution time should be < 10ms
```

### 3. Data Integrity Testing

```sql
-- Verify no data loss
WITH original_counts AS (
    SELECT count(*) as old_total FROM todos
),
new_counts AS (
    SELECT count(*) as new_total FROM (
        SELECT id FROM todos_active
        UNION ALL
        SELECT id FROM todos_archived
    ) combined
)
SELECT 
    old_total,
    new_total,
    CASE WHEN old_total = new_total THEN 'PASS' ELSE 'FAIL' END as integrity_check
FROM original_counts, new_counts;
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Migration Takes Too Long
**Problem:** Migration script runs for hours
**Solution:**
```sql
-- Adjust batch size
SELECT * FROM migrate_todos_batch(500, 10); -- Smaller batches, limit runs
```

#### 2. Partition Pruning Not Working
**Problem:** Queries scan all partitions instead of specific ones
**Solution:**
```sql
-- Ensure WHERE clause includes user_id
-- Wrong:
SELECT * FROM todos_active WHERE title = 'something';

-- Correct:
SELECT * FROM todos_active WHERE user_id = $1 AND title = 'something';
```

#### 3. Foreign Key Issues
**Problem:** Cannot create foreign keys across partitions
**Solution:** Handle referential integrity in application layer:
```python
async def create_todo_with_parent(self, todo_data, user_id):
    # Validate parent exists in same user's partition
    if todo_data.parent_todo_id:
        parent = await self.get_todo_by_id(todo_data.parent_todo_id, user_id)
        if not parent:
            raise TodoNotFoundError("Parent todo not found")
    
    return await self.create_todo(todo_data, user_id)
```

#### 4. Index Not Being Used
**Problem:** Queries still slow despite indexes
**Solution:**
```sql
-- Check if index exists and is being used
EXPLAIN (ANALYZE, BUFFERS) your_query_here;

-- Update table statistics
ANALYZE todos_active;

-- Consider rewriting query to match index
```

#### 5. Archive Partitions Growing Too Large
**Problem:** Monthly archive partitions become huge
**Solution:**
```sql
-- Switch to weekly partitions for high-volume periods
CREATE TABLE todos_archived_2025_01_w1 PARTITION OF todos_archived 
    FOR VALUES FROM ('2025-01-01') TO ('2025-01-08');
```

## 📊 Monitoring and Maintenance

### Daily Monitoring Queries

```sql
-- Check partition sizes
SELECT * FROM get_partition_statistics() ORDER BY size_mb DESC;

-- Check maintenance job status
SELECT * FROM maintenance_history WHERE started_at >= CURRENT_DATE - INTERVAL '7 days';

-- Monitor query performance
SELECT * FROM get_index_usage_stats() WHERE index_scans < 10;
```

### Weekly Health Checks

```sql
-- Run comprehensive health check
SELECT * FROM check_partition_health();

-- Verify archival is working
SELECT 
    count(*) as active_done_todos 
FROM todos_active 
WHERE status = 'done' AND completed_at < CURRENT_DATE - INTERVAL '30 days';
-- Should be close to 0

-- Check data distribution
SELECT 
    substring(tablename from 'todos_active_part_(\d+)') as partition,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size
FROM pg_tables 
WHERE tablename LIKE 'todos_active_part_%'
ORDER BY partition::int;
```

## 🔄 Rollback Plan

If you need to rollback to the original structure:

```sql
-- 1. Stop the application

-- 2. Restore original data (if original table still exists)
INSERT INTO todos 
SELECT 
    id, user_id, parent_todo_id, project_id, title, description,
    status, priority, due_date, completed_at, ai_generated,
    created_at, updated_at
FROM todos_active
UNION ALL
SELECT 
    id, user_id, parent_todo_id, project_id, title, description,
    status, priority, due_date, completed_at, ai_generated,
    created_at, updated_at  
FROM todos_archived;

-- 3. Update application to use original Todo model

-- 4. Drop partitioned tables (after verification)
-- DROP TABLE todos_active CASCADE;
-- DROP TABLE todos_archived CASCADE;
```

## 🎯 Success Metrics

After implementation, you should see:

| Metric | Before | Target After |
|--------|--------|--------------|
| User todo query time | 2-5 seconds | 50-200ms |
| Dashboard load time | 5-10 seconds | 500ms-1s |
| Database backup time | 4-8 hours | 30-60 minutes |
| Storage growth rate | Linear | Logarithmic |
| Query scalability | Degrades with users | Constant performance |

## 📚 Additional Resources

- [PostgreSQL Partitioning Documentation](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [SQLAlchemy 2.0 Migration Guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [Database Scaling Best Practices](database-scaling-strategy.md)

## 🆘 Support and Questions

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs in `maintenance_job_log` table
3. Run validation queries to identify specific problems
4. Consider rolling back if critical issues occur

---

**Remember:** Always test in a staging environment first and maintain recent backups throughout the implementation process.