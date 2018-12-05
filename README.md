# eventernote-api
Crawl eventernote.com and expose JSON or RSS

## Dependencies
* Python 3.7.0

## Prepare
* Recommended: Prepare a virtualenv of Python 3.7.0 named `eventernote-api-venv`
* `pip install -r requirements.txt`

## Run
```
FLASK_ENV=development python app.py
```
* Actor events as JSON: `localhost:5000/json/三森すずこ/2634`
* Actor events as RSS: `localhost:5000/rss/三森すずこ/2634`

## Configurations
* Environment variables
    * `EVENT_EXPIRE_SECONDS`: Number of seconds before in-memory cache for events expires for an actor. Default to 6 hours
