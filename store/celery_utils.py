import logging

logger = logging.getLogger(__name__)


def safe_delay(task, *args, **kwargs):
    """Queue a Celery task; skip gracefully if Redis/broker is unavailable."""
    try:
        return task.delay(*args, **kwargs)
    except Exception as exc:
        logger.warning(
            'Celery broker unavailable, task %s skipped: %s',
            getattr(task, 'name', task),
            exc,
        )
        return None
