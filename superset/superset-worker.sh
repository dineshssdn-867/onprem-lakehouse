#!/bin/bash
set -e

echo ">>> Superset Worker: Starting Celery worker..."
exec celery \
  --app=superset.tasks.celery_app:app \
  worker \
  --loglevel=INFO \
  --pool=prefork \
  --concurrency=2
