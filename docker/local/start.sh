#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o xtrace


# python manage.py migrate
python3 manage.py runserver_plus --cert-file /tmp/cert.crt 0.0.0.0:8000
