import logging as xlogging
from typing import Dict
from apscheduler.schedulers.background import BackgroundScheduler
from .logging import config_logger
from .events import events

logger = xlogging.getLogger("worker")
config_logger(logger)

def work(
    events_cache: Dict
):
    if not events_cache:
        logger.info("No work to run")
    else:
        for local_id, _ in events_cache.items():
            actor_name, actor_id = local_id
            if events_cache[local_id]['locked']:
                logger.info(f"{actor_name} is locked")
            else:
                logger.info(f"{actor_name} is not locked, locking and crawling")
                events_cache[local_id]['locked'] = True
                events_cache[local_id]['data'] = events(actor_name=actor_name, actor_id=actor_id)
                events_cache[local_id]['locked'] = False

def start_worker(
    events_cache: Dict,
    events_expire_seconds: int
):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: work(events_cache), 'interval', seconds=events_expire_seconds)
    scheduler.start()
