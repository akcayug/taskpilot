#!/bin/bash
set -e

echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

echo "Setting up Django..."
export DJANGO_SETTINGS_MODULE=taskpilot.settings

echo "Starting bot with healthz server..."
exec python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskpilot.settings')
django.setup()

from bot.healthz import start_healthz_server
from bot.main import main

start_healthz_server()
main()
"
