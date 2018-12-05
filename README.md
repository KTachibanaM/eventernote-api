# eventernote-api
Crawl eventernote.com and expose JSON or RSS

## Dependencies
* Python 3.7.0

## Prepare
* Recommended: Prepare a virtualenv of Python 3.7.0 named `eventernote-api-venv`
* `pip install -r requirements.txt`

## Run
```
python -m flask run
```

## Configurations
* Environment variables
    * `EVENT_EXPIRE_SECONDS`: Number of seconds before in-memory cache for events expires for an actor. Default to 6 hours
