"""Task scheduler for SMZDM Bot.

Provides scheduled task execution using APScheduler.
"""

import signal
import sys
from random import randint

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from smzdm_bot.config import get_settings
from smzdm_bot.main import run_tasks


def get_schedule_time() -> tuple[int, int, str]:
    """Determine scheduled execution time.

    Returns:
        Tuple of (hour, minute, timezone).
    """
    settings = get_settings()
    scheduler_config = settings.get_scheduler_config()

    hour = scheduler_config.hour
    minute = scheduler_config.minute
    timezone = scheduler_config.timezone

    if hour is None:
        hour = randint(6, 10)
        logger.info(f"No SMZDM_SCH_HOUR set, using random hour: {hour}")

    if minute is None:
        minute = randint(0, 59)
        logger.info(f"No SMZDM_SCH_MINUTE set, using random minute: {minute}")

    return hour, minute, timezone


def scheduled_task() -> None:
    """Execute scheduled tasks."""
    logger.info("=" * 50)
    logger.info("Starting scheduled task execution")
    logger.info("=" * 50)

    try:
        run_tasks()
    except Exception as e:
        logger.exception(f"Scheduled task failed: {e}")

    logger.info("Scheduled task completed")


def run_scheduler() -> None:
    """Start the task scheduler.

    1. Runs tasks immediately on startup
    2. Schedules future runs at the configured time
    3. Handles graceful shutdown
    """
    # Run immediately on startup
    logger.info("Running initial task execution...")
    try:
        run_tasks()
    except Exception as e:
        logger.error(f"Initial task execution failed: {e}")

    # Get schedule time
    hour, minute, timezone = get_schedule_time()
    logger.info(f"Scheduled time: {hour:02d}:{minute:02d} ({timezone})")

    # Create scheduler
    scheduler = BlockingScheduler(timezone=timezone)

    trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)
    scheduler.add_job(
        scheduled_task,
        trigger=trigger,
        id="smzdm_checkin",
        name="SMZDM Daily Check-in",
        replace_existing=True,
    )

    # Graceful shutdown
    def shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start
    logger.info("Scheduler started. Waiting for next run...")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    run_scheduler()
