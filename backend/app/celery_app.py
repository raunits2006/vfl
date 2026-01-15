from celery import Celery
from celery.schedules import crontab, timedelta  # Import crontab and timedelta
from app.core.config import settings

# Initialize Celery
# The first argument is the name of the current module, this is needed so that names can be generated automatically when tasks are defined.
# The broker argument specifies the URL of the message broker you want to use (Redis in this case).
# The backend argument specifies the result backend to use (also Redis).
celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.workers.match_updater',
             'app.workers.live_match_scraper',
             'app.workers.draft_autopick',
             ]  # List of modules to import when the worker starts.
)

# Optional Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Optional: if you want to store task results for a shorter/longer time
    # result_expires=3600, # 1 hour
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    'update-matches-nightly': {
        'task': 'app.workers.match_updater.update_upcoming_matches_task',
        'schedule': crontab(minute=0, hour=0),  # Run at midnight UTC daily
        # Optionally, you can pass arguments to the task if it accepts them:
        # 'args': (arg1, arg2),
    },
}

celery_app.conf.beat_schedule.update({
    'scrape-live-matches-every-90-seconds': {
        'task': 'app.workers.maybe_trigger_scrape_live_matches',
        'schedule': timedelta(seconds=90),
    },
    'check-expired-draft-picks-every-30-seconds': {
        'task': 'app.workers.draft_autopick.check_expired_picks',
        'schedule': timedelta(seconds=30),  # Every 30 seconds for more responsive autopicks
    },
})



if __name__ == '__main__':
    celery_app.start()
