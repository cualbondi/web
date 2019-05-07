#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


python3 /app/manage.py collectstatic --noinput
/usr/local/bin/gunicorn config.wsgi --reuse-port --workers=10 --threads=100 -b 0.0.0.0:8000 --chdir=/app
