import re
import copy
import logging as xlogging
import sys
import os
import time
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import quote
from flask import Flask, jsonify

logger = xlogging.getLogger("app.py")
logger.setLevel(xlogging.INFO)
logger.addHandler(xlogging.StreamHandler(stream=sys.stdout))


def current_seconds():
    return int(round(time.time()))


EVENT_EXPIRE_SECONDS = int(os.environ.get("EVENT_EXPIRE_SECONDS", 6 * 60 * 60))
logger.info("EVENT_EXPIRE_SECONDS=" + str(EVENT_EXPIRE_SECONDS))

EVENT_CRAWLING_LIMIT = 100
EVENT_LINK_PREFIX = "/events/"
date_re = re.compile("(\d{4})-(\d{2})-(\d{2})")


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

    def __str__(self):
        return "ParsingException url=" + self.url + " layers=" + str(self.layers) + " message=" + self.message


events_cache = {}


def events(actor_name: str, actor_id: str) -> List[Dict]:
    if actor_name in events_cache\
            and current_seconds() < events_cache[actor_name]['last_crawl_seconds'] + EVENT_EXPIRE_SECONDS:
        logger.info("Events not expired for actor_name=" + actor_name + " actor_id=" + actor_id)
        return events_cache[actor_name]['data']

    logger.info("Crawling events for actor_name=" + actor_name + " actor_id=" + actor_id)
    res = []
    page = 1

    while True:
        url = "https://www.eventernote.com/actors/" + quote(actor_name) + "/" + actor_id + "/events?actor_id="\
              + actor_id + "&limit=" + str(EVENT_CRAWLING_LIMIT) + "&page=" + str(page)
        logger.info("Crawling " + url)
        ex = ParsingException(url)

        html = urlopen(url).read()
        soup = BeautifulSoup(html, "html.parser")
        event_li_list = soup.select("li.clearfix")
        if not event_li_list:
            logger.debug("Cannot find more event_li_list at page=" + str(page))
            break

        for i, event_li in enumerate(event_li_list):
            event_li_ex = ex.add_layer("li.clearfix[" + str(i) + "]")

            date_p = event_li.select_one("div.date > p")
            if not date_p:
                event_li_ex.raise_me("cannot find date_p")
            date_text = date_p.getText()
            date_matches = date_re.match(date_text).groups()
            if len(date_matches) != 3:
                event_li_ex.raise_me("date_text matches are not of length 3")
            year = int(date_matches[0])
            month = int(date_matches[1])
            day = int(date_matches[2])

            title_a = event_li.select_one("div.event > h4 > a")
            if not title_a:
                event_li_ex.raise_me("cannot find title_a")
            if not title_a["href"].startswith(EVENT_LINK_PREFIX):
                event_li_ex.raise_me("title_a href does not start with " + EVENT_LINK_PREFIX)
            _id = title_a["href"][len(EVENT_LINK_PREFIX):]
            title = title_a.getText()

            res.append({
                "id": _id,
                "year": year,
                "month": month,
                "day": day,
                "title": title
            })
        page += 1

    events_cache[actor_name] = {}
    events_cache[actor_name]['last_crawl_seconds'] = current_seconds()
    events_cache[actor_name]['data'] = res

    logger.info("Crawled " + str(len(res)) + " events for actor_name=" + actor_name + " actor_id=" + actor_id)
    return res


app = Flask(__name__)


@app.route('/json/<name>/<_id>')
def json(name: str, _id: str):
    return jsonify(events(actor_name=name, actor_id=_id))