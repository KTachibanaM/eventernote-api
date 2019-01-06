import logging as xlogging
from apscheduler.schedulers.background import BackgroundScheduler
from .logging import config_logger
from .events import events

logger = xlogging.getLogger("worker")
config_logger(logger)

def work(
    events_cache: dict
):
    logger.info("Running work")
    for local_id, _ in events_cache.items():
        logger.info(f"Running work for {local_id}")

def start_worker(
    events_cache: dict,
    events_expire_seconds: int
):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: work(events_cache), 'interval', seconds=events_expire_seconds)
    scheduler.start()
