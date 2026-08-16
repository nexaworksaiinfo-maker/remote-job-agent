"""Celery configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "remote_job_agent",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
    include=[
        "app.tasks.scraper_tasks",
        "app.tasks.matcher_tasks",
        "app.tasks.application_tasks",
        "app.tasks.notification_tasks",
    ],
)

# Celery config
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    result_expires=3600,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_routes={
        "app.tasks.scraper_tasks.*": {"queue": "scrapers"},
        "app.tasks.matcher_tasks.*": {"queue": "matchers"},
        "app.tasks.application_tasks.*": {"queue": "applications"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)

# Beat schedule
celery_app.conf.beat_schedule = {
    # Scraping - every 6 hours
    "scrape-all-sources": {
        "task": "app.tasks.scraper_tasks.scrape_all_sources",
        "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
    },
    # Enrich job details - every 3 hours
    "enrich-job-details": {
        "task": "app.tasks.scraper_tasks.enrich_job_details",
        "schedule": crontab(hour="*/3", minute=30),
    },
    # Matching - every 2 hours
    "match-all-profiles": {
        "task": "app.tasks.matcher_tasks.match_all_profiles",
        "schedule": crontab(hour="*/2", minute=15),
    },
    # Generate embeddings - daily at 3 AM
    "generate-embeddings": {
        "task": "app.tasks.matcher_tasks.generate_embeddings",
        "schedule": crontab(hour=3, minute=0),
    },
    # Process applications - every 15 minutes
    "process-application-queue": {
        "task": "app.tasks.application_tasks.process_application_queue",
        "schedule": crontab(minute="*/15"),
    },
    # Retry failed - hourly
    "retry-failed-applications": {
        "task": "app.tasks.application_tasks.retry_failed_applications",
        "schedule": crontab(minute=0),
    },
    # Follow-ups - daily at 9 AM
    "follow-up-applications": {
        "task": "app.tasks.application_tasks.follow_up_applications",
        "schedule": crontab(hour=9, minute=0),
    },
    # Check status - every 4 hours
    "check-application-status": {
        "task": "app.tasks.application_tasks.check_application_status",
        "schedule": crontab(hour="*/4", minute=0),
    },
    # Notifications - daily digests at 8 AM
    "send-daily-digests": {
        "task": "app.tasks.notification_tasks.send_daily_digests",
        "schedule": crontab(hour=8, minute=0),
    },
    # Weekly summaries - Monday 9 AM
    "send-weekly-summaries": {
        "task": "app.tasks.notification_tasks.send_weekly_summaries",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
    # Cleanup - daily at 2 AM
    "cleanup-old-data": {
        "task": "app.tasks.maintenance_tasks.cleanup_old_data",
        "schedule": crontab(hour=2, minute=0),
    },
    # Update company data - weekly Sunday 3 AM
    "update-company-data": {
        "task": "app.tasks.scraper_tasks.update_company_data",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
}

if __name__ == "__main__":
    celery_app.start()