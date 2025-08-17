#!/bin/bash

# Maintenance Cron Setup Script
# This script sets up automated maintenance scheduling for the partitioned todo system
# Run this script on your production server to automate database maintenance

# Database connection string - adjust as needed
DB_CONNECTION="postgresql://neondb_owner:npg_FWhBl3ZoRLE0@ep-cool-violet-abkekvp1-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require"

echo "Setting up automated maintenance for TodoList database scaling system"
echo "======================================================================="

# Create log directory for maintenance logs
mkdir -p /var/log/todolist-maintenance

# Create daily maintenance script
cat > /usr/local/bin/todolist-daily-maintenance << 'EOF'
#!/bin/bash
LOG_FILE="/var/log/todolist-maintenance/daily-$(date +%Y%m%d).log"
echo "$(date): Starting daily maintenance" >> $LOG_FILE

psql "$DB_CONNECTION" -c "SELECT * FROM run_daily_maintenance();" >> $LOG_FILE 2>&1

echo "$(date): Daily maintenance completed" >> $LOG_FILE
EOF

# Create weekly maintenance script
cat > /usr/local/bin/todolist-weekly-maintenance << 'EOF'
#!/bin/bash
LOG_FILE="/var/log/todolist-maintenance/weekly-$(date +%Y%m%d).log"
echo "$(date): Starting weekly maintenance" >> $LOG_FILE

psql "$DB_CONNECTION" -c "SELECT * FROM run_weekly_maintenance();" >> $LOG_FILE 2>&1

echo "$(date): Weekly maintenance completed" >> $LOG_FILE
EOF

# Make scripts executable
chmod +x /usr/local/bin/todolist-daily-maintenance
chmod +x /usr/local/bin/todolist-weekly-maintenance

# Add cron jobs
echo "Adding cron jobs for automated maintenance..."

# Daily maintenance at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/todolist-daily-maintenance") | crontab -

# Weekly maintenance at 3 AM on Sundays
(crontab -l 2>/dev/null; echo "0 3 * * 0 /usr/local/bin/todolist-weekly-maintenance") | crontab -

echo "Maintenance scheduling setup complete!"
echo ""
echo "Scheduled jobs:"
echo "- Daily maintenance: 2:00 AM (archive completed todos, create partitions)"
echo "- Weekly maintenance: 3:00 AM Sundays (vacuum, health checks)"
echo ""
echo "Log files will be created in: /var/log/todolist-maintenance/"
echo ""
echo "To monitor maintenance status, you can:"
echo "1. Check logs: tail -f /var/log/todolist-maintenance/daily-$(date +%Y%m%d).log"
echo "2. Query database: SELECT * FROM maintenance_history ORDER BY started_at DESC;"
echo "3. Check partition health: SELECT * FROM partition_monitor WHERE vacuum_status != 'OK';"
echo ""
echo "Manual maintenance commands:"
echo "- Run daily maintenance: psql \"$DB_CONNECTION\" -c \"SELECT * FROM run_daily_maintenance();\""
echo "- Run weekly maintenance: psql \"$DB_CONNECTION\" -c \"SELECT * FROM run_weekly_maintenance();\""
echo "- Archive old todos: psql \"$DB_CONNECTION\" -c \"SELECT * FROM archive_completed_todos(30, 1000);\""