#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


python /app/manage.py collectstatic --noinput
/usr/local/bin/gunicorn config.wsgi -w 20 -b 0.0.0.0:8000 --chdir=/app
