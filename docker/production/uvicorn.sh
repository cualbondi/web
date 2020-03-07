#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


python3 /app/manage.py collectstatic --noinput
python3 /app/manage.py compilemessages
uvicorn config.asgi:application --host 0.0.0.0 --port 8000
