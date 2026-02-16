import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskpilot.settings')

# Create Celery app
app = Celery('taskpilot')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'send-daily-reminders': {
        'task': 'workers.tasks.send_daily_reminders',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM every day
    },
    'send-due-today-notifications': {
        'task': 'workers.tasks.send_due_today_notifications',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM every day
    },
}

# Configure timezone
app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing"""
    print(f'Request: {self.request!r}')
