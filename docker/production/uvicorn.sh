#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


/venv/bin/python3 /app/manage.py collectstatic --noinput
/venv/bin/python3 /app/manage.py compilemessages
/venv/bin/uvicorn config.asgi:application --host 0.0.0.0 --port 8000
