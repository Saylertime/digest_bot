from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import atexit
import pytz

from .parser import daily_digest_job


def tasks_checker():
    scheduler = AsyncIOScheduler()
    scheduler.start()
    tz = pytz.timezone("Europe/Moscow")

    scheduler.add_job(
        func=daily_digest_job,
        # trigger=IntervalTrigger(seconds=10),
        trigger=CronTrigger(
            hour=11,
            minute=00,
            day_of_week="0-4",
            timezone=tz
        ),
        id="send_daily_digest_job",
        name="Отправка новых материалов",
        replace_existing=True,
    )

    atexit.register(lambda: scheduler.shutdown())
