__all__ = ["init_scheduler", "register_job"]

from os import getenv
from datetime import timezone
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.base import BaseTrigger
from app.core.logging import get_logger

logger = get_logger()

_scheduler: Optional[BackgroundScheduler] = None
_app = None


def init_scheduler(app) -> None:
    """
    Initialize the background scheduler. Should be called once during app setup,
    BEFORE any register_job() calls from services.
    
    :param app: The Flask app instance, used for app_context wrapping
    """
    global _scheduler, _app
    
    if _scheduler is not None:
        logger.debug("Scheduler already initialized, skipping")
        return
    
    if getenv("DISABLE_SCHEDULER", "false").lower() == "true":
        logger.info("Scheduler disabled via DISABLE_SCHEDULER")
        return
    
    _app = app
    _scheduler = BackgroundScheduler(
        timezone=timezone.utc,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 3600,
        }
    )
    
    _scheduler.start()
    logger.info("Scheduler started")
    
    import atexit
    atexit.register(_shutdown)


def register_job(
    func: Callable,
    trigger: BaseTrigger,
    job_id: str,
    name: Optional[str] = None,
) -> None:
    """
    Register a job with the scheduler. The function will automatically be wrapped
    in the Flask app context, so services can use current_app, Database, etc.
    
    :param func: The function to execute (no arguments)
    :param trigger: APScheduler trigger (e.g. CronTrigger, IntervalTrigger)
    :param job_id: Unique identifier for the job
    :param name: Optional human-readable job name
    """
    if _scheduler is None:
        if getenv("DISABLE_SCHEDULER", "false").lower() == "true":
            logger.debug(f"Scheduler disabled, skipping registration of '{job_id}'")
            return
        raise RuntimeError(
            f"Cannot register job '{job_id}': scheduler not initialized. "
            "Call init_scheduler(app) first."
        )
    
    if _app is None:
        raise RuntimeError("Scheduler is missing app context")
    
    captured_app = _app
    
    def wrapped():
        try:
            with captured_app.app_context():
                func()
        except Exception as e:
            logger.exception(f"Job '{job_id}' crashed: {e}")
    
    _scheduler.add_job(
        func=wrapped,
        trigger=trigger,
        id=job_id,
        name=name or job_id,
        replace_existing=True,
    )
    
    logger.info(f"Registered scheduled job: {job_id}")


def _shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler shutdown complete")