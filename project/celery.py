from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Scheduled Tasks
app.conf.beat_schedule = {

    'daily-sales-summary': {
        'task': 'store.tasks.run_adaptive_sales_job',
        'schedule': crontab(),
    },
}