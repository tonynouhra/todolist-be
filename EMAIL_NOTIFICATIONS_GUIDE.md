# Email Notifications System - Complete Guide

## Overview

The TodoList application includes a comprehensive email notification system that sends daily reminders to users about:
- **Tasks expiring soon** (within 3 days)
- **Pending tasks** (tasks in "todo" status)

The system uses:
- **Celery** for background task processing
- **Celery Beat** for scheduling daily notifications
- **Redis** as the message broker
- **SMTP** for email delivery

## Architecture

```
┌─────────────────┐       ┌──────────────┐       ┌─────────────────┐
│   Celery Beat   │──────>│    Redis     │<──────│  Celery Worker  │
│   (Scheduler)   │       │   (Broker)   │       │   (Processor)   │
└─────────────────┘       └──────────────┘       └─────────────────┘
                                                           │
                                                           v
                                                  ┌─────────────────┐
                                                  │  Email Service  │
                                                  │     (SMTP)      │
                                                  └─────────────────┘
                                                           │
                                                           v
                                                  ┌─────────────────┐
                                                  │     Users       │
                                                  │   (Recipients)  │
                                                  └─────────────────┘
```

## Setup Instructions

### 1. Configure Email Settings

Update your `.env` file with SMTP configuration:

```bash
# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com           # Your SMTP server
SMTP_PORT=587                      # SMTP port (usually 587 for TLS)
SMTP_USER=your-email@gmail.com     # Your email address
SMTP_PASSWORD=your-app-password    # App password (not regular password)
EMAIL_FROM=noreply@yourdomain.com  # From address (optional)
```

#### Gmail Setup

1. **Enable 2-Factor Authentication** in your Google Account
2. **Generate App Password**:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Select "2-Step Verification"
   - Scroll to "App passwords"
   - Generate a new app password for "Mail"
   - Use this password in `SMTP_PASSWORD`

3. **Configure Environment**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # 16-character app password
EMAIL_FROM=noreply@yourdomain.com
```

#### Outlook/Office 365 Setup

```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
EMAIL_FROM=your-email@outlook.com
```

#### SendGrid Setup

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=verified-sender@yourdomain.com
```

### 2. Configure Celery

Already configured in `.env`:

```bash
# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

For Docker (auto-configured in docker-compose.yml):
```bash
CELERY_BROKER_URL=redis://:redispass@redis:6379/1
CELERY_RESULT_BACKEND=redis://:redispass@redis:6379/2
```

### 3. User Notification Preferences

Users can control their notification settings via the `user_settings` table:

- `notifications_enabled` - Master switch for all notifications
- `email_notifications` - Enable/disable email notifications
- `timezone` - User's timezone (for future time-based features)

**Default Values:**
- `notifications_enabled`: `true`
- `email_notifications`: `true`

Users without settings records will receive notifications by default.

## Running the System

### Option 1: Docker (Recommended)

1. **Start all services**:
```bash
docker-compose up -d
```

This starts:
- `postgres` - Database
- `redis` - Message broker
- `backend` - FastAPI application
- `celery-worker` - Background task processor
- `celery-beat` - Task scheduler
- `nginx` - Reverse proxy

2. **View logs**:
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
```

3. **Stop services**:
```bash
docker-compose down
```

### Option 2: Local Development

1. **Start Redis**:
```bash
redis-server
```

2. **Start FastAPI Backend**:
```bash
cd todolist-be
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. **Start Celery Worker** (in new terminal):
```bash
cd todolist-be
celery -A app.celery_app worker --loglevel=info --concurrency=4 -Q notifications
```

4. **Start Celery Beat** (in new terminal):
```bash
cd todolist-be
celery -A app.celery_app beat --loglevel=info
```

## Schedule Configuration

The default schedule is configured in `app/celery_app.py`:

```python
celery_app.conf.beat_schedule = {
    "send-daily-reminders": {
        "task": "app.tasks.notification_tasks.send_daily_reminders_task",
        "schedule": crontab(hour=9, minute=0),  # 9:00 AM UTC daily
        "options": {"expires": 3600},
    },
}
```

### Customizing the Schedule

To change the notification time, modify the `crontab`:

```python
# Daily at 8:00 AM UTC
crontab(hour=8, minute=0)

# Daily at 6:00 PM UTC
crontab(hour=18, minute=0)

# Every Monday at 9:00 AM UTC
crontab(hour=9, minute=0, day_of_week=1)

# Twice daily (9 AM and 6 PM UTC)
crontab(hour='9,18', minute=0)
```

**Important:** All times are in UTC. Convert your local time to UTC:
- PST (UTC-8): 9 AM PST = 5 PM UTC
- EST (UTC-5): 9 AM EST = 2 PM UTC
- CET (UTC+1): 9 AM CET = 8 AM UTC

## Testing

### 1. Test Email Service (Direct)

Create a test script:

```python
# test_email.py
import asyncio
from app.services.email_service import email_service

def test_email():
    success = email_service.send_email(
        to_email="your-email@example.com",
        subject="Test Email",
        html_content="<h1>Test Email</h1><p>If you receive this, SMTP is working!</p>",
        text_content="Test Email - SMTP is working!"
    )
    print(f"Email sent: {success}")

if __name__ == "__main__":
    test_email()
```

Run:
```bash
python test_email.py
```

### 2. Test via API Endpoint

**Send Test Reminder:**
```bash
curl -X POST http://localhost:8000/api/notifications/test-reminder \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Check Task Status:**
```bash
curl http://localhost:8000/api/notifications/task-status/{task_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Test via Celery Task Directly

```python
# test_celery.py
from app.tasks.notification_tasks import send_test_reminder_task

# Queue the task
task = send_test_reminder_task.delay("your-email@example.com")
print(f"Task ID: {task.id}")

# Check status
from app.celery_app import celery_app
result = celery_app.AsyncResult(task.id)
print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

### 4. Trigger Daily Reminder Manually

```python
# test_daily_reminder.py
from app.tasks.notification_tasks import send_daily_reminders_task

# Run immediately
result = send_daily_reminders_task.apply()
print(f"Result: {result.get()}")
```

Or via Celery:
```bash
celery -A app.celery_app call app.tasks.notification_tasks.send_daily_reminders_task
```

## Email Template

The system sends beautifully designed HTML emails with:

### Email Features

1. **Gradient Header** with TodoList AI branding
2. **Expiring Tasks Section**:
   - Red/orange theme
   - Shows tasks due within 3 days
   - Includes priority, title, description, due date
3. **Pending Tasks Section**:
   - Blue theme
   - Shows tasks in "todo" status
   - Ordered by priority (high first)
   - Limited to 10 tasks (with "... and X more" message)
4. **Call-to-Action Button** linking to the app
5. **Settings Link** to manage notification preferences
6. **Responsive Design** for mobile/desktop
7. **Plain Text Fallback** for email clients that don't support HTML

### Priority Colors

- **Very High (5)**: Red (#ef4444)
- **High (4)**: Orange (#f97316)
- **Medium (3)**: Amber (#f59e0b)
- **Low (2)**: Blue (#3b82f6)
- **Very Low (1)**: Green (#10b981)

## Notification Logic

### Tasks Expiring Soon

```python
# Checks for tasks:
- Status: "todo" or "in_progress"
- Has due_date set
- due_date is within next 3 days
- Orders by due_date (earliest first)
```

### Pending Tasks

```python
# Checks for tasks:
- Status: "todo"
- Orders by priority (high first), then created_at (oldest first)
- Limits to 20 tasks
```

### User Filtering

```python
# Only sends to users who:
- is_active = true
- Has UserSettings with:
  - notifications_enabled = true
  - email_notifications = true
- OR has no UserSettings (defaults to enabled)
```

## Monitoring & Debugging

### View Celery Worker Logs

**Docker:**
```bash
docker-compose logs -f celery-worker
```

**Local:**
Check terminal where worker is running

### View Celery Beat Logs

**Docker:**
```bash
docker-compose logs -f celery-beat
```

**Local:**
Check terminal where beat is running

### Check Redis Queue

```bash
# Connect to Redis
redis-cli

# Or in Docker
docker exec -it todolist_redis redis-cli -a redispass

# Check queue length
LLEN celery

# View tasks
LRANGE celery 0 10
```

### Monitor Task Execution

```python
# Via Flower (Celery monitoring tool)
pip install flower

celery -A app.celery_app flower
# Visit http://localhost:5555
```

### Common Issues

#### 1. Emails Not Sending

**Check SMTP Configuration:**
```python
from app.services.email_service import email_service

# Validate config
if email_service._validate_config():
    print("✅ SMTP configured correctly")
else:
    print("❌ SMTP configuration missing or invalid")
```

**Check Logs:**
```bash
docker-compose logs celery-worker | grep "email"
```

**Test SMTP Connection:**
```python
import smtplib
from app.core.config import settings

try:
    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
    server.starttls()
    server.login(settings.smtp_user, settings.smtp_password)
    print("✅ SMTP connection successful")
    server.quit()
except Exception as e:
    print(f"❌ SMTP error: {e}")
```

#### 2. Celery Worker Not Processing Tasks

**Check Worker Status:**
```bash
celery -A app.celery_app inspect active
celery -A app.celery_app inspect stats
```

**Check Redis Connection:**
```bash
redis-cli ping
# Should return: PONG
```

**Restart Worker:**
```bash
docker-compose restart celery-worker
```

#### 3. Celery Beat Not Scheduling

**Check Beat Status:**
```bash
docker-compose logs celery-beat | grep "beat"
```

**Verify Schedule:**
```python
from app.celery_app import celery_app

print(celery_app.conf.beat_schedule)
```

**Restart Beat:**
```bash
docker-compose restart celery-beat
```

#### 4. No Users Receiving Emails

**Check User Settings:**
```sql
SELECT
    u.email,
    us.notifications_enabled,
    us.email_notifications,
    u.is_active
FROM users u
LEFT JOIN user_settings us ON u.id = us.user_id
WHERE u.is_active = true;
```

**Check for Tasks:**
```sql
-- Expiring tasks
SELECT COUNT(*)
FROM todos
WHERE status IN ('todo', 'in_progress')
  AND due_date IS NOT NULL
  AND due_date BETWEEN NOW() AND NOW() + INTERVAL '3 days';

-- Pending tasks
SELECT COUNT(*)
FROM todos
WHERE status = 'todo';
```

## Performance Considerations

### Task Concurrency

The worker runs with `concurrency=4` (4 parallel tasks):

```bash
celery -A app.celery_app worker --concurrency=4
```

For high-volume systems, increase concurrency:
```bash
celery -A app.celery_app worker --concurrency=8
```

### Rate Limiting

To avoid overwhelming SMTP servers:

```python
# In app/celery_app.py
celery_app.conf.task_default_rate_limit = '10/m'  # 10 tasks per minute
```

### Email Batching

For large user bases, consider batching:

```python
# Process in batches of 100 users
BATCH_SIZE = 100
```

## API Endpoints

### POST /api/notifications/test-reminder

Send a test reminder to the current user.

**Request:**
```bash
POST /api/notifications/test-reminder
Authorization: Bearer {token}
```

**Response:**
```json
{
  "status": "success",
  "message": "Test reminder email queued successfully...",
  "data": {
    "task_id": "abc-123-def-456",
    "email": "user@example.com",
    "status": "queued"
  }
}
```

### GET /api/notifications/task-status/{task_id}

Get the status of a background task.

**Request:**
```bash
GET /api/notifications/task-status/abc-123-def-456
Authorization: Bearer {token}
```

**Response:**
```json
{
  "status": "success",
  "message": "Task status retrieved successfully",
  "data": {
    "task_id": "abc-123-def-456",
    "status": "SUCCESS",
    "result": {
      "success": true,
      "email": "user@example.com"
    }
  }
}
```

## Security Best Practices

1. **Never commit `.env` file** - Contains sensitive SMTP credentials
2. **Use app passwords** instead of regular passwords for Gmail
3. **Enable TLS/SSL** for SMTP connections (port 587 with STARTTLS)
4. **Validate email addresses** before sending
5. **Rate limit email sending** to prevent abuse
6. **Encrypt SMTP credentials** in production environments
7. **Use verified sender addresses** for SendGrid/SES

## Future Enhancements

- [ ] Support for multiple timezones (send at user's local 9 AM)
- [ ] Digest email options (daily/weekly)
- [ ] Custom notification frequencies
- [ ] SMS notifications via Twilio
- [ ] Push notifications for mobile apps
- [ ] Email template customization per user
- [ ] Unsubscribe link in emails
- [ ] Email bounce handling
- [ ] Email open/click tracking

## Troubleshooting Commands

```bash
# Check all services status
docker-compose ps

# Restart specific service
docker-compose restart celery-worker

# View live logs
docker-compose logs -f celery-worker celery-beat

# Enter container shell
docker exec -it todolist_celery_worker bash

# Test Celery connection
celery -A app.celery_app inspect ping

# Clear Celery queue
celery -A app.celery_app purge

# Check scheduled tasks
celery -A app.celery_app inspect scheduled
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review this guide
3. Check `.env` configuration
4. Test SMTP connection directly
5. Open an issue on GitHub

---

**Happy Coding! 📧✨**
