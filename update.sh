#!/bin/bash

heroku git:remote -a fractal-monitor-server && \
git add . && \
git commit -m "pushing to production" && \
git push heroku master:master && \
heroku run:detached python monitor.py && \
curl -X POST --data-urlencode "payload={\"channel\": \"#general\", \"username\": \"fractal-bot\", \"text\": \"Monitor-Webserver Updated in Production on Heroku\", \"icon_emoji\": \":ghost:\"}" https://hooks.slack.com/services/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
