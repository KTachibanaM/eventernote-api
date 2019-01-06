import sys
import logging as xlogging

def config_logger(logger):
    logger.setLevel(xlogging.INFO)
    handler = xlogging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(xlogging.Formatter('[%(name)s][%(asctime)s][%(levelname)s] %(message)s'))
    logger.addHandler(handler)
