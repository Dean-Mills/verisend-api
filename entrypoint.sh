#!/bin/bash
if [ "$APP_MODE" = "worker" ]; then
    exec celery -A verisent.workers.celery_app worker --loglevel=info
else
    exec uvicorn verisent.main:app --host 0.0.0.0 --port 80
fi