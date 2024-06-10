#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


/venv/bin/python3 /app/manage.py collectstatic --noinput
/venv/bin/python3 /app/manage.py compilemessages
/venv/bin/gunicorn config.wsgi --reuse-port --workers=10 --threads=100 -b 0.0.0.0:8000 --chdir=/app
