#!/bin/bash
if [ "$APP_MODE" = "worker" ]; then
    exec celery -A verisend.workers.celery_app worker --loglevel=info
else
    exec uvicorn verisend.main:app --host 0.0.0.0 --port 80
fi