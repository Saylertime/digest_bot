from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

from .parser import fetch_all


def tasks_checker():
    scheduler = AsyncIOScheduler()
    scheduler.start()

    scheduler.add_job(
        func=fetch_all,
        trigger=IntervalTrigger(seconds=3),
        id="send_message_job",
        name="Проверка Django API каждые 2 секунды",
        replace_existing=True,
    )

    atexit.register(lambda: scheduler.shutdown())
