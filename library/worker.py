import logging as xlogging
from .logging import config_logger
from .events import events

logger = xlogging.getLogger("worker")
config_logger(logger)

def work(
    events_cache: dict
):
    for local_id, _ in events_cache.items():
        logger.info(local_id)
