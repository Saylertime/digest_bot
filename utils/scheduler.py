from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import atexit

from .parser import fetch_all


def tasks_checker():
    scheduler = AsyncIOScheduler()
    scheduler.start()

    scheduler.add_job(
        func=fetch_all,
        trigger=IntervalTrigger(hours=2),
        id="send_message_job",
        name="Отправка новых материалов",
        replace_existing=True,
    )

    # scheduler.add_job(
    #     func=fetch_all,
    #     trigger=CronTrigger(hour=12, minute=00),
    #     id="check_subscriptions_job",
    #     name="Отправка новых материалов",
    #     replace_existing=True,
    # )

    atexit.register(lambda: scheduler.shutdown())
