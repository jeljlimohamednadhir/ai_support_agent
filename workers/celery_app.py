"""
Celery Worker Configuration
"""
from celery import Celery
from celery.schedules import crontab

# Create Celery app
celery_app = Celery(
    "genergy_ia",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "workers.code_analyzer",
    "workers.log_analyzer",
    "workers.db_analyzer",
    "workers.doc_analyzer",
    "workers.jira_sync",
    "workers.graph_builder"
])

# Celery Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    # Sync Jira every hour
    'sync-jira-hourly': {
        'task': 'workers.jira_sync.scheduled_sync',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Rebuild graph every 6 hours
    'rebuild-graph': {
        'task': 'workers.graph_builder.scheduled_build',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
}
