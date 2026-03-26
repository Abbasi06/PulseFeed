from __future__ import annotations

from celery.schedules import crontab

from .celery_app import app

app.conf.beat_schedule = {
    "harvest-arxiv-6h": {
        "task": "generator.tasks.harvest_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": ["arxiv", "machine learning systems distributed inference", 30],
    },
    "harvest-github-12h": {
        "task": "generator.tasks.harvest_task",
        "schedule": crontab(minute=30, hour="*/12"),
        "args": ["github", "llm inference optimization runtime", 20],
    },
    "harvest-rss-3h": {
        "task": "generator.tasks.harvest_task",
        "schedule": crontab(minute=15, hour="*/3"),
        "args": [
            "rss",
            "feeds:https://feeds.feedburner.com/oreilly/radar,https://engineeringblogs.xyz/feed.xml keyword:engineering",
            25,
        ],
    },
}
