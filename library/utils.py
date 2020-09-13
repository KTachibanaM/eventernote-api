import os
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
        self.sentry_enabled = 'SENTRY_DSN' in os.environ

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
        if self.sentry_enabled:
            logger.error("ParsingException", extra={
                'url': self.url,
                'layers': self.layers,
                '_message': self.message
            })
        else:
            print(str(self))
        raise self

    def warn_me(self, message: str):
        self.message = message
        print(str(self))

    def __str__(self):
        return "ParsingException url=" + self.url + " layers=" + str(self.layers) + " message=" + self.message
