"""Main entry point for SMZDM Bot."""

from loguru import logger

from smzdm_bot.client import SmzdmClient
from smzdm_bot.config import Settings, UserConfig, get_settings
from smzdm_bot.models import TaskResult
from smzdm_bot.notify import send_notification
from smzdm_bot.tasks import TaskRunner


def run_user(user: UserConfig) -> TaskResult:
    """Execute all tasks for a single user."""
    try:
        with SmzdmClient(user) as client:
            runner = TaskRunner(client)
            return runner.run_all()
    except Exception as e:
        logger.error(f"User {user.name} failed: {e}")
        return TaskResult(user_id=user.name or "unknown", success=False, error=str(e))


def run_all(settings: Settings | None = None) -> list[TaskResult]:
    """Execute tasks for all users."""
    settings = settings or get_settings()
    users = settings.get_users()

    logger.info(f"Running tasks for {len(users)} user(s)")
    results = [run_user(user) for user in users]

    # Send notification
    notify = settings.get_notify_config()
    if notify.has_any_provider and results:
        ok = sum(1 for r in results if r.success)
        send_notification(
            notify,
            title=f"SMZDM ({ok}/{len(results)})",
            content="\n\n".join(r.to_message() for r in results),
        )

    return results


def main() -> int:
    """CLI entry point."""
    results = run_all()

    if not results:
        logger.warning("No users configured")
        return 1

    failed = sum(1 for r in results if not r.success)
    if failed:
        logger.warning(f"{failed} user(s) failed")
        return 1

    logger.success("All done!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
