import re
import copy
import logging as xlogging
import sys
import os
import time
import pytz
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import quote
from feedgen.feed import FeedGenerator
from datetime import datetime
from ics import Calendar
from ics import Event as iCalEvent
from arrow import Arrow
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
time_re = re.compile("開場 (\d{2}):(\d{2}) 開演 (\d{2}):(\d{2}) 終演 (\d{2}):(\d{2})")
time_re_2 = re.compile("開場 - 開演 (\d{2}):(\d{2}) 終演 (\d{2}):(\d{2})")


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


def event_base_link(actor_name: str, actor_id: str) -> str:
    return f"https://www.eventernote.com/actors/{quote(actor_name)}/{actor_id}/events"


def event_link(event_id: str):
    return f"https://www.eventernote.com/events/{event_id}"


EVENTS_CACHE = {}


class Event(object):
    def __init__(self, _id: str, title: str, year: int, month: int, day: int):
        self._id = _id
        self.title = title
        self.year = year
        self.month = month
        self.day = day
        self.open_hour = None
        self.open_minute = None
        self.start_hour = None
        self.start_minute = None
        self.end_hour = None
        self.end_minute = None
        self.place = None

    def set_open_hour_minute(self, hour: int, minute: int):
        self.open_hour = hour
        self.open_minute = minute

    def set_start_hour_minute(self, hour: int, minute: int):
        self.start_hour = hour
        self.start_minute = minute

    def set_end_hour_minute(self, hour: int, minute: int):
        self.end_hour = hour
        self.end_minute = minute

    def get_time_arrows(self) -> Tuple[Optional[Arrow], Optional[Arrow], Optional[Arrow]]:
        if not self.year:
            return None, None, None
        open_arrow, start_arrow, end_arrow = None, None, None
        if self.open_hour:
            open_arrow = Arrow(
                year=self.year,
                month=self.month,
                day=self.day,
                tzinfo=pytz.timezone("Asia/Tokyo"),
                hour=self.open_hour,
                minute=self.open_minute)
        if self.start_hour:
            start_arrow = Arrow(
                year=self.year,
                month=self.month,
                day=self.day,
                tzinfo=pytz.timezone("Asia/Tokyo"),
                hour=self.start_hour,
                minute=self.start_minute
            )
        if self.end_hour:
            end_arrow = Arrow(
                year=self.year,
                month=self.month,
                day=self.day,
                tzinfo=pytz.timezone("Asia/Tokyo"),
                hour=self.end_hour,
                minute=self.end_minute
            )
            open_or_start_hour = self.open_hour or self.start_hour
            open_or_start_minute = self.open_minute or self.start_minute
            if open_or_start_hour and\
                    (open_or_start_hour > self.end_hour or
                     (open_or_start_hour == self.end_hour and open_or_start_minute >= self.end_minute)):
                end_arrow = end_arrow.replace(days=1)
        return open_arrow, start_arrow, end_arrow

    def as_dict(self):
        d = {
            "id": self._id,
            "title": self.title
        }
        open_arrow, start_arrow, end_arrow = self.get_time_arrows()
        if open_arrow:
            d["open_time"] = {
                "year": open_arrow.datetime.year,
                "month": open_arrow.datetime.month,
                "day": open_arrow.datetime.day,
                "hour": open_arrow.datetime.hour,
                "minute": open_arrow.datetime.minute
            }
        if start_arrow:
            d["start_time"] = {
                "year": start_arrow.datetime.year,
                "month": start_arrow.datetime.month,
                "day": start_arrow.datetime.day,
                "hour": start_arrow.datetime.hour,
                "minute": start_arrow.datetime.minute
            }
        if end_arrow:
            d["end_time"] = {
                "year": end_arrow.datetime.year,
                "month": end_arrow.datetime.month,
                "day": end_arrow.datetime.day,
                "hour": end_arrow.datetime.hour,
                "minute": end_arrow.datetime.minute
            }
        return d


def events(actor_name: str, actor_id: str) -> List[Event]:
    if actor_name in EVENTS_CACHE\
            and current_seconds() < EVENTS_CACHE[actor_name]['last_crawl_seconds'] + EVENT_EXPIRE_SECONDS:
        logger.info("Events not expired for actor_name=" + actor_name + " actor_id=" + actor_id)
        return EVENTS_CACHE[actor_name]['data']

    logger.info("Crawling events for actor_name=" + actor_name + " actor_id=" + actor_id)
    all_events = []
    page = 1

    while True:
        url = event_base_link(actor_name=actor_name, actor_id=actor_id)\
              + "?actor_id=" + actor_id\
              + "&limit=" + str(EVENT_CRAWLING_LIMIT)\
              + "&page=" + str(page)
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

            title_a = event_li.select_one("div.event > h4 > a")
            if not title_a:
                event_li_ex.raise_me("cannot find title_a")
            if not title_a["href"].startswith(EVENT_LINK_PREFIX):
                event_li_ex.raise_me("title_a href does not start with " + EVENT_LINK_PREFIX)
            _id = title_a["href"][len(EVENT_LINK_PREFIX):]
            title = title_a.getText()

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

            cur_event = Event(_id=_id, title=title, year=year, month=month, day=day)

            place_a = event_li.select_one("div.event > div.place > a")
            if place_a:
                cur_event.place = place_a.getText()
            else:
                event_li_ex.warn_me("cannot find place_a")

            time_span = event_li.select_one("div.event > div.place > span.s")
            if time_span:
                time_text = time_span.getText()
                time_match_group = time_re.match(time_text)
                if time_match_group:
                    time_matches = time_match_group.groups()
                    if len(time_matches) != 6:
                        event_li_ex.warn_me("time_matches are not of length 6")
                    else:
                        cur_event.set_open_hour_minute(hour=int(time_matches[0]), minute=int(time_matches[1]))
                        cur_event.set_start_hour_minute(hour=int(time_matches[2]), minute=int(time_matches[3]))
                        cur_event.set_end_hour_minute(hour=int(time_matches[4]), minute=int(time_matches[5]))
                else:
                    time_match_group_2 = time_re_2.match(time_text)
                    if time_match_group_2:
                        time_matches_2 = time_match_group_2.groups()
                        if len(time_matches_2) != 4:
                            event_li_ex.warn_me("time_matches_2 are not of length 4")
                        else:
                            cur_event.set_start_hour_minute(hour=int(time_matches_2[0]), minute=int(time_matches_2[1]))
                            cur_event.set_end_hour_minute(hour=int(time_matches_2[2]), minute=int(time_matches_2[3]))
                    else:
                        event_li_ex.warn_me(f"cannot match {time_text} time_text with time_re or time_re_2")
            else:
                event_li_ex.warn_me("cannot find time_span")

            all_events.append(cur_event)
        page += 1

    EVENTS_CACHE[actor_name] = {}
    EVENTS_CACHE[actor_name]['last_crawl_seconds'] = current_seconds()
    EVENTS_CACHE[actor_name]['data'] = all_events

    logger.info("Crawled " + str(len(all_events)) + " events for actor_name=" + actor_name + " actor_id=" + actor_id)
    return all_events


app = Flask(__name__)


@app.route('/')
def index():
    return """
I'am alive!<br/>
/json/三森すずこ/2634: Events for 三森すずこ(id=2634) in JSON<br/>
/rss/三森すずこ/2634: Events for 三森すずこ(id=2634) in RSS<br/>
/debug
"""


@app.route('/debug')
def debug():
    return jsonify({
        'events_cache': {
            'actors_size': len(EVENTS_CACHE.keys()),
            'actors': list(EVENTS_CACHE.keys()),
            'events_size': sum(map(lambda a: len(a['data']), list(EVENTS_CACHE.values())))
        }
    })


@app.route('/json/<name>/<_id>')
def json(name: str, _id: str):
    return jsonify(list(map(lambda e: e.as_dict(), events(actor_name=name, actor_id=_id))))


@app.route('/rss/<name>/<_id>')
def rss(name: str, _id: str):
    fg = FeedGenerator()
    events_link = event_base_link(actor_name=name, actor_id=_id)
    fg.id(events_link)
    fg.title(name + "のイベント・ライブ情報一覧")
    fg.description(name + "のイベント・ライブ情報一覧")
    fg.link(href=events_link, rel='alternate')
    fg.language("ja")
    for event in events(actor_name=name, actor_id=_id):
        fe = fg.add_entry()
        fe.id(event._id)
        fe.link(href=event_link(event._id))
        fe.title(f"{event.year}/{event.month}/{event.day} {event.title}")
        fe.pubDate(datetime(
            year=event.year,
            month=event.month,
            day=event.day,
            tzinfo=pytz.timezone("Asia/Tokyo")
        ))
    return fg.rss_str(pretty=True)


@app.route('/ical/<name>/<_id>')
def ical(name: str, _id: str):
    c = Calendar()
    for event in events(actor_name=name, actor_id=_id):
        e = iCalEvent(
            name=event.title,
            uid=event._id,
            url=event_link(event._id)
        )
        e.location = event.place
        open_arrow, start_arrow, end_arrow = event.get_time_arrows()
        e.begin = open_arrow or start_arrow
        e.end = end_arrow
        c.events.add(e)
    return str(c)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
