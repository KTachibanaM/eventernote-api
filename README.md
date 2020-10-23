**DEPRECATED**

The project has been deprecated in favor of an RSS route in RSSHub

See doc here https://docs.rsshub.app/anime.html#eventernote

# eventernote-api
Crawl eventernote.com and expose JSON or RSS

## Dependencies
* `Python 3.7`
* `virtualenv`

## Prepare
```bash
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
source ./venv/bin/activate
FLASK_ENV=development python app.py
```

* Actor events as JSON: [`localhost:5000/json/三森すずこ/2634`](localhost:5000/json/三森すずこ/2634)
* Actor events as RSS: [`localhost:5000/rss/三森すずこ/2634`](localhost:5000/rss/三森すずこ/2634)
* Actor events as iCal: [`localhost:5000/ical/三森すずこ/2634`](localhost:5000/ical/三森すずこ/2634)

## Configurations
* Environment variables
    * `EVENT_EXPIRE_SECONDS`: Number of seconds before in-memory cache for events expires for an actor. Default to 6 hours
    * `SENTRY_DSN`: Sentry DSN. If not set, errors will not be sent to Sentry
