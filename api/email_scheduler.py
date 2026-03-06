"""
APScheduler-based tick job that checks all active email schedules
every 60 seconds and triggers email sending when a time slot matches.
"""
import logging
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Track (user_id, "HH:MM", date_str) to avoid duplicate sends within the same minute
_sent_tracker: dict[str, bool] = {}


def _cleanup_tracker():
    """Remove stale entries older than today to prevent unbounded growth."""
    today = datetime.now().strftime("%Y-%m-%d")
    keys_to_remove = [k for k in _sent_tracker if not k.endswith(today)]
    for k in keys_to_remove:
        del _sent_tracker[k]


def _get_active_configs_sync():
    """Query all active EmailScheduleConfig records (sync ORM)."""
    from main_app.models import EmailScheduleConfig
    return list(
        EmailScheduleConfig.objects.filter(is_active=True)
        .select_related('user')
    )


async def tick_job():
    """
    Runs every 60 seconds. For each active schedule, check if current time
    in the user's timezone matches any send_time slot.
    """
    from django.db import close_old_connections
    close_old_connections()

    try:
        configs = await sync_to_async(_get_active_configs_sync)()
    except Exception as e:
        logger.error(f"Email scheduler tick: failed to query configs: {e}")
        return

    if not configs:
        return

    _cleanup_tracker()

    for config in configs:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(config.timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("Asia/Shanghai")

        now_in_tz = datetime.now(tz)
        current_hhmm = now_in_tz.strftime("%H:%M")
        date_str = now_in_tz.strftime("%Y-%m-%d")

        for slot in (config.send_times or []):
            if slot != current_hhmm:
                continue

            tracker_key = f"{config.user_id}:{slot}:{date_str}"
            if tracker_key in _sent_tracker:
                continue

            _sent_tracker[tracker_key] = True
            logger.info(
                f"Email scheduler: triggering email for user {config.user_id} "
                f"at slot {slot} ({config.timezone})"
            )

            asyncio.create_task(_safe_send(config.user_id))


async def _safe_send(user_id: int):
    """Send email with error isolation so one failure doesn't block others."""
    try:
        from api.email_service import send_story_email
        result = await send_story_email(user_id)
        if result["status"] == "failed":
            logger.warning(f"Email scheduler: send failed for user {user_id}: {result.get('error')}")
    except Exception as e:
        logger.error(f"Email scheduler: unexpected error for user {user_id}: {e}", exc_info=True)


def start_scheduler():
    """Start the APScheduler (call from FastAPI startup event)."""
    scheduler.add_job(tick_job, 'interval', seconds=60, id='email_tick', replace_existing=True)
    scheduler.start()
    logger.info("Email scheduler started (60s tick interval)")


def shutdown_scheduler():
    """Shut down the APScheduler gracefully."""
    scheduler.shutdown(wait=False)
    logger.info("Email scheduler shut down")
