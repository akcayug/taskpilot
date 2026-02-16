#!/bin/bash
set -e

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis is ready!"

echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Start healthz server in background
echo "Starting healthz server..."
python -c "from workers.healthz import run_healthz_background; run_healthz_background()" &

echo "Starting Celery worker with beat..."
exec celery -A workers.celery_app worker --beat --loglevel=info
