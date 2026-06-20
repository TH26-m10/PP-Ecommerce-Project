#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from project.db_compat import allow_local_mariadb

allow_local_mariadb()

import django

django.setup()

from django.db import connection
from django.db.utils import OperationalError

for attempt in range(60):
    try:
        connection.ensure_connection()
        print("Database is ready.")
        break
    except OperationalError:
        time.sleep(2)
else:
    raise SystemExit("Database not available after 120 seconds.")
PY

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput --fake-initial
fi

exec "$@"
