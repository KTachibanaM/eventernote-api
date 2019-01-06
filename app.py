import logging as xlogging
import os
import pytz
import threading
from feedgen.feed import FeedGenerator
from datetime import datetime
from ics import Calendar
from ics import Event as iCalEvent
from flask import Flask, jsonify
from library.events import cached_events, event_link, event_base_link
from library.logging import config_logger
from library.worker import start_worker

app = Flask(__name__)
config_logger(app.logger)

EVENTS_CACHE = {}

EVENT_EXPIRE_SECONDS = int(os.environ.get("EVENT_EXPIRE_SECONDS", 6 * 60 * 60))
app.logger.info("EVENT_EXPIRE_SECONDS=" + str(EVENT_EXPIRE_SECONDS))

start_worker(EVENTS_CACHE, EVENT_EXPIRE_SECONDS)


@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html lang="jp">
<head>
    <title>eventernote-api</title>
</head>
<body>
    I'am alive!<br/>
    <a href="/json/三森すずこ/2634">/json/三森すずこ/2634</a> Events for 三森すずこ(id=2634) in JSON<br/>
    <a href="/rss/三森すずこ/2634">/rss/三森すずこ/2634</a> Events for 三森すずこ(id=2634) in RSS<br/>
    <a href="/ical/三森すずこ/2634">/ical/三森すずこ/2634</a> Events for 三森すずこ(id=2634) in ical<br/>
    <a href="/debug">/debug</a>
</body>
</html>
"""


@app.route('/debug')
def debug():
    return jsonify({
        'events_cache': {
            'actors_size': len(EVENTS_CACHE.keys()),
            'actors': list(map(lambda k: k[0], EVENTS_CACHE.keys())),
            'events_size': sum(map(lambda a: len(a['data']), list(EVENTS_CACHE.values())))
        }
    })


@app.route('/json/<name>/<_id>')
def json(name: str, _id: str):
    return jsonify(list(map(lambda e: e.as_dict(), cached_events(
        actor_name=name,
        actor_id=_id,
        events_cache=EVENTS_CACHE
    ))))


@app.route('/rss/<name>/<_id>')
def rss(name: str, _id: str):
    fg = FeedGenerator()
    events_link = event_base_link(actor_name=name, actor_id=_id)
    fg.id(events_link)
    fg.title(name + "のイベント・ライブ情報一覧")
    fg.description(name + "のイベント・ライブ情報一覧")
    fg.link(href=events_link, rel='alternate')
    fg.language("ja")
    for event in cached_events(
            actor_name=name,
            actor_id=_id,
            events_cache=EVENTS_CACHE
    ):
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
    for event in cached_events(
            actor_name=name,
            actor_id=_id,
            events_cache=EVENTS_CACHE
    ):
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
