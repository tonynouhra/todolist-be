# Email Notifications - Quick Start Guide

## What's New? 📧

Your TodoList app now sends daily email reminders about:
- ⏰ **Tasks expiring soon** (within 3 days)
- 📝 **Pending tasks** waiting to be done

## Quick Setup (5 minutes)

### 1. Configure Email (`.env`)

```bash
# For Gmail (Recommended for Testing)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App password from Google
EMAIL_FROM=noreply@yourdomain.com
```

**Get Gmail App Password:**
1. Enable 2FA on your Google Account
2. Visit: [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate password for "Mail"
4. Copy 16-character password to `SMTP_PASSWORD`

### 2. Start with Docker

```bash
# Start all services (includes Celery worker & beat)
docker-compose up -d

# View logs
docker-compose logs -f celery-worker celery-beat
```

### 3. Test It!

**Option A: Via API**
```bash
curl -X POST http://localhost:8000/api/notifications/test-reminder \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Option B: Via Python**
```python
from app.tasks.notification_tasks import send_test_reminder_task

task = send_test_reminder_task.delay("your-email@example.com")
print(f"Task ID: {task.id}")
```

## When Are Emails Sent?

**Daily at 9:00 AM UTC** (default)

**Change the time** in `app/celery_app.py`:
```python
crontab(hour=9, minute=0)  # 9 AM UTC
```

## Architecture

```
Docker Compose Services:
├── postgres      ─── Database
├── redis         ─── Message broker
├── backend       ─── FastAPI app
├── celery-worker ─── Processes email tasks ✨ NEW
├── celery-beat   ─── Schedules daily job  ✨ NEW
└── nginx         ─── Reverse proxy
```

## Files Created

```
todolist-be/
├── app/
│   ├── services/
│   │   ├── email_service.py         ✨ Email sending logic
│   │   └── notification_service.py  ✨ Task checking logic
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── notification_tasks.py    ✨ Celery tasks
│   ├── domains/notification/
│   │   ├── __init__.py
│   │   └── controller.py            ✨ API endpoints
│   ├── celery_app.py                ✨ Celery configuration
│   └── main.py                      ⚙️  Updated (added router)
├── docker-compose.yml               ⚙️  Updated (added services)
├── .env.example                     ⚙️  Updated (added email config)
└── EMAIL_NOTIFICATIONS_GUIDE.md     ✨ Full documentation
```

## User Settings

Users control notifications in `user_settings`:
- `notifications_enabled` - Master switch
- `email_notifications` - Email notifications on/off
- `timezone` - User's timezone

**Defaults:** All enabled

## Troubleshooting

### Emails not sending?

1. **Check SMTP config:**
```python
from app.services.email_service import email_service
print(email_service._validate_config())  # Should be True
```

2. **Check Celery worker logs:**
```bash
docker-compose logs celery-worker | grep "email"
```

3. **Test SMTP directly:**
```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email', 'your-app-password')
print("✅ SMTP works!")
server.quit()
```

### Celery not running?

```bash
# Check services
docker-compose ps

# Restart Celery
docker-compose restart celery-worker celery-beat

# View logs
docker-compose logs -f celery-worker celery-beat
```

### No emails received?

1. **Check user settings:**
```sql
SELECT email, notifications_enabled, email_notifications
FROM users u
LEFT JOIN user_settings us ON u.id = us.user_id
WHERE u.is_active = true;
```

2. **Check for tasks:**
```sql
-- Any expiring tasks?
SELECT COUNT(*) FROM todos
WHERE status IN ('todo', 'in_progress')
  AND due_date BETWEEN NOW() AND NOW() + INTERVAL '3 days';

-- Any pending tasks?
SELECT COUNT(*) FROM todos WHERE status = 'todo';
```

## Next Steps

1. ✅ Configure SMTP in `.env`
2. ✅ Start Docker services
3. ✅ Test with `/api/notifications/test-reminder`
4. ✅ Check your inbox!
5. 📖 Read full guide: `EMAIL_NOTIFICATIONS_GUIDE.md`

## Support

- 📚 Full Guide: `EMAIL_NOTIFICATIONS_GUIDE.md`
- 🐛 Issues: Check logs first
- 💬 Questions: Open GitHub issue

---

**That's it! Your users will now get daily task reminders! 🎉**
