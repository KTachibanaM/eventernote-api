import pytz
import re
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import quote
from arrow import Arrow
from . import logger
from .regex import RegexMatch, match_regex_in_order
from .utils import current_seconds, ParsingException

EVENT_CRAWLING_LIMIT = 100
EVENT_LINK_PREFIX = "/events/"


date_re = re.compile("(\d{4})-(\d{2})-(\d{2})")
time_re_1 = re.compile("開場 (\d{2}):(\d{2}) 開演 (\d{2}):(\d{2}) 終演 (\d{2}):(\d{2})")
time_re_2 = re.compile("開場 - 開演 (\d{2}):(\d{2}) 終演 (\d{2}):(\d{2})")
time_re_3 = re.compile("開場 (\d{2}):(\d{2}) 開演 - 終演 (\d{2}):(\d{2})")


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


def event_base_link(actor_name: str, actor_id: str) -> str:
    return f"https://www.eventernote.com/actors/{quote(actor_name)}/{actor_id}/events"


def event_link(event_id: str):
    return f"https://www.eventernote.com/events/{event_id}"


def cached_events(
    actor_name: str,
    actor_id: str,
    events_cache: dict,
):
    local_id = (actor_name, actor_id)
    if local_id in events_cache:
        return events_cache[actor_name]['data']

    new_events = events(actor_name=actor_name, actor_id=actor_id)

    events_cache[local_id] = {}
    events_cache[local_id]['data'] = new_events
    
    return new_events


def events(
        actor_name: str,
        actor_id: str
) -> List[Event]:
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

                def no(): pass

                def eval_1(matches: List[str]) -> bool:
                    if len(matches) != 6:
                        event_li_ex.warn_me("time_re_1 is not of length 6")
                        return False
                    cur_event.set_open_hour_minute(hour=int(matches[0]), minute=int(matches[1]))
                    cur_event.set_start_hour_minute(hour=int(matches[2]), minute=int(matches[3]))
                    cur_event.set_end_hour_minute(hour=int(matches[4]), minute=int(matches[5]))
                    return True
                match_1 = RegexMatch(
                    regex=time_re_1,
                    no_matches_func=no,
                    eval_matches_func=eval_1
                )

                def eval_2(matches: List[str]) -> bool:
                    if len(matches) != 4:
                        event_li_ex.warn_me("time_re_2 is not of length 4")
                        return False
                    cur_event.set_start_hour_minute(hour=int(matches[0]), minute=int(matches[1]))
                    cur_event.set_end_hour_minute(hour=int(matches[2]), minute=int(matches[3]))
                    return True
                match_2 = RegexMatch(
                    regex=time_re_2,
                    no_matches_func=no,
                    eval_matches_func=eval_2
                )

                def eval_3(matches: List[str]) -> bool:
                    if len(matches) != 4:
                        event_li_ex.warn_me("time_re_3 is not of length 4")
                        return False
                    cur_event.set_open_hour_minute(hour=int(matches[0]), minute=int(matches[1]))
                    cur_event.set_end_hour_minute(hour=int(matches[2]), minute=int(matches[3]))
                    return True
                match_3 = RegexMatch(
                    regex=time_re_3,
                    no_matches_func=no,
                    eval_matches_func=eval_3
                )

                def final(): event_li_ex.warn_me(f"{time_text} cannot match any re")
                match_regex_in_order(
                    time_text,
                    [match_1, match_2, match_3],
                    final
                )
            else:
                event_li_ex.warn_me("cannot find time_span")

            all_events.append(cur_event)
        page += 1

    logger.info("Crawled " + str(len(all_events)) + " events for actor_name=" + actor_name + " actor_id=" + actor_id)
    return all_events
