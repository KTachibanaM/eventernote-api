import time
import copy
from . import logger


def current_seconds():
    return int(round(time.time()))


class ParsingException(Exception):
    def __init__(self, url: str):
        self.url = url
        self.layers = []
        self.message = "No message"

    def clone(self):
        new_ex = ParsingException(self.url)
        new_ex.layers = copy.copy(self.layers)
        return new_ex

    def add_layer(self, layer_name: str):
        new_ex = self.clone()
        new_ex.layers.append(layer_name)
        return new_ex

    def raise_me(self, message: str):
        self.message = message
        logger.error(str(self))
        raise self

    def warn_me(self, message: str):
        self.message = message
        logger.warning(str(self))

    def __str__(self):
        return "ParsingException url=" + self.url + " layers=" + str(self.layers) + " message=" + self.message
