import logging as xlogging
from .logging import config_logger

logger = xlogging.getLogger("library")
config_logger(logger)
