# PostgreSQL Hash Partitioning Analysis

## Overview
Analysis of the `todos_active` table partitioning behavior in the TodoList database.

## Issue Investigated
User observed data in `todos_active` table but not in `todos_active_part_xx` partitions.

## Database Structure

### Partitioning Setup
- **Parent Table**: `todos_active`
- **Partition Key**: `HASH(user_id)`
- **Number of Partitions**: 16 (part_00 through part_15)
- **Partition Method**: Hash partitioning with modulus 16

### Partition Distribution
Each partition handles a specific remainder when the user_id hash is divided by 16:
- `todos_active_part_00`: remainder 0
- `todos_active_part_01`: remainder 1
- ...
- `todos_active_part_15`: remainder 15

## Current Data Distribution

### Analysis Results
- **Total Records**: 16 rows in `todos_active`
- **User Count**: 1 user (`40e142fd-1038-48e6-93ae-15edba5c5c43`)
- **Active Partition**: `todos_active_part_09` (contains all 16 rows)
- **Empty Partitions**: All other partitions (00-08, 10-15)

### Hash Calculation
```sql
-- User ID hash calculation
SELECT satisfies_hash_partition('todos_active'::regclass, 16, 9, '40e142fd-1038-48e6-93ae-15edba5c5c43'::uuid) as matches_partition_09;
-- Result: true
```

## Key Findings

### Why Data Appears Only in Part_09
1. **Single User Scenario**: All current data belongs to one user
2. **Hash Function Result**: User ID `40e142fd-1038-48e6-93ae-15edba5c5c43` hashes to remainder 9
3. **Correct Behavior**: PostgreSQL correctly places all rows in `todos_active_part_09`

### Verification Queries
```sql
-- Check total count in parent table
SELECT COUNT(*) FROM todos_active; -- Result: 16

-- Check partition distribution
SELECT tableoid::regclass as table_location, COUNT(*) as count
FROM todos_active
GROUP BY tableoid;
-- Result: todos_active_part_09 contains 16 rows

-- Verify individual partitions
SELECT COUNT(*) FROM todos_active_part_09; -- Result: 16
SELECT COUNT(*) FROM todos_active_part_00; -- Result: 0
```

## Conclusion

### System is Working Correctly
- ✅ Hash partitioning is functioning as designed
- ✅ Data is properly distributed based on user_id hash
- ✅ PostgreSQL automatically routes queries to appropriate partitions
- ✅ No data loss or corruption

### Expected Behavior with More Users
As new users are added to the system:
- Each user's todos will be distributed to their hash-determined partition
- Data will spread across multiple partitions based on user_id hash values
- Load will be distributed more evenly across all 16 partitions

### No Action Required
The partitioning system is operating correctly. The apparent "missing" data in partitions is actually correct behavior for a single-user scenario in a hash-partitioned table.

## Frequently Asked Questions

### Q: Should the `todos_active` table be empty?
**A:** No, the `todos_active` parent table should **appear to have data** when queried, but it's actually a **logical view** of all its partitions combined.

**How it works:**
- The parent table `todos_active` has **no physical storage** - it's purely a logical view
- When you query `todos_active`, PostgreSQL automatically searches all relevant partitions
- The actual data lives in the partition tables (`todos_active_part_XX`)
- Results are returned as if querying a single unified table

### Q: Is `todos_active` a view of all partition tables?
**A:** Exactly! `todos_active` is essentially a **virtual union** of all partition tables.

When you query:
```sql
SELECT * FROM todos_active;
```

PostgreSQL internally performs something conceptually like:
```sql
-- Behind the scenes (simplified concept)
SELECT * FROM todos_active_part_00
UNION ALL
SELECT * FROM todos_active_part_01
UNION ALL
-- ... (but only searches partitions that could contain matching data)
SELECT * FROM todos_active_part_09  -- Your data is here
UNION ALL
-- ... rest of partitions
```

**But it's much more efficient because:**
- **Partition Pruning**: Only searches partitions that could contain your data
- **Direct Routing**: In your case, goes directly to `part_09` based on user_id hash
- **No Actual Union**: No expensive union operations - just intelligent query routing

**Key Points:**
- Parent table = Virtual orchestrator with no physical storage
- Partition tables = Physical storage locations
- Query results = Seamless combination of relevant partition data

### Q: Is `todos_active` a normal table, view, or something else?
**A:** `todos_active` is a **Partitioned Table** - a special type that's neither a normal table nor a view.

**PostgreSQL Classification:**
```sql
-- Check table types
SELECT relname, relkind,
       CASE relkind
         WHEN 'r' THEN 'ordinary table'
         WHEN 'v' THEN 'view'
         WHEN 'p' THEN 'partitioned table'
       END as table_type
FROM pg_class
WHERE relname IN ('todos_active', 'todos_active_part_09');

-- Results:
-- todos_active: 'p' = partitioned table
-- todos_active_part_09: 'r' = ordinary table
```

**How it differs from each type:**

**vs Normal Table:**
```sql
-- Normal table: stores data physically
CREATE TABLE normal_todos (id UUID, title TEXT);
INSERT INTO normal_todos VALUES ('123', 'Buy milk');
-- ↑ Data stored directly in normal_todos

-- Partitioned table: NO physical storage
CREATE TABLE todos_active (id UUID, title TEXT) PARTITION BY HASH(user_id);
INSERT INTO todos_active VALUES ('456', 'Walk dog');
-- ↑ Data automatically routed to partition (todos_active_part_XX)
```

**vs View:**
```sql
-- View: Just a saved query definition
CREATE VIEW active_todos_view AS
  SELECT * FROM todos WHERE status = 'active';
-- ↑ No table structure, just query logic

-- Partitioned table: Real table structure + intelligent routing
CREATE TABLE todos_active (...) PARTITION BY HASH(user_id);
-- ↑ Has real columns, constraints, indexes, BUT no data storage
```

**What `todos_active` actually is:**
- ✅ **Has real table structure** (columns, types, constraints, indexes)
- ✅ **You can INSERT/UPDATE/DELETE** directly into it
- ✅ **PostgreSQL automatically routes** data to correct partition
- ✅ **Enforces data integrity** across all partitions
- ❌ **Stores no data itself** - all data physically lives in partitions

**Think of it as a "Smart Router Table":**
- More than a view (has real structure and can be modified)
- Less than a normal table (no physical storage)
- Acts as intelligent dispatcher to partition tables

### Q: So `todos_active` is virtual with no physical data, and PostgreSQL handles the routing automatically?
**A:** Exactly! You've understood it perfectly!

`todos_active` is a **partitioned table** that:

1. ✅ **Contains NO physical data** - it's virtual/logical
2. ✅ **When you INSERT**, PostgreSQL automatically:
   - Takes the `user_id`
   - Calculates hash of `user_id`
   - Divides by 16 to get remainder (0-15)
   - Stores data in the corresponding partition table
3. ✅ **When you SELECT**, PostgreSQL automatically:
   - Shows you data from all relevant partitions
   - Makes it appear as one unified table

**Physical Storage Proof:**
```sql
SELECT pg_size_pretty(pg_relation_size('todos_active')) as parent_table_size,
       pg_size_pretty(pg_relation_size('todos_active_part_09')) as partition_09_size;

-- Results:
-- parent_table_size: "0 bytes" (no physical storage!)
-- partition_09_size: "8192 bytes" (actual data lives here!)
```

**The Process:**
- `todos_active` = Virtual container/router (0 bytes storage)
- Physical data = Stored in partition tables (8192+ bytes)
- Hash calculation = `user_id` hash ÷ 16 = remainder determines partition
- What you see = Virtual unified view of all partitions combined

**Analogy - Smart Mailbox System:**
- `todos_active` = Main mailbox (you put letters in here)
- PostgreSQL = Mail sorter (automatically routes to correct box)
- `todos_active_part_XX` = Individual storage boxes (where letters actually live)
- When you check mail = You see all letters from all boxes as if from one mailbox

**Key Insight:** The data you see when querying `todos_active` is not physically stored there - it's a real-time aggregation from the partition tables where the actual data lives!

## Related Information
- **Database**: Neon PostgreSQL
- **Project ID**: jolly-queen-02911405
- **Analysis Date**: September 14, 2025
- **PostgreSQL Version**: 17