# eventernote-api
Crawl eventernote.com and expose JSON or RSS

## Dependencies
* `Python`
* `pipenv`

## Run
```
./dev.sh
```
* Actor events as JSON: [`localhost:5000/json/三森すずこ/2634`](localhost:5000/json/三森すずこ/2634)
* Actor events as RSS: [`localhost:5000/rss/三森すずこ/2634`](localhost:5000/rss/三森すずこ/2634)
* Actor events as iCal: [`localhost:5000/ical/三森すずこ/2634`](localhost:5000/ical/三森すずこ/2634)

## Configurations
* Environment variables
    * `EVENT_EXPIRE_SECONDS`: Number of seconds before in-memory cache for events expires for an actor. Default to 6 hours
