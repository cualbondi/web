#!/bin/bash

set -o nounset
set -o xtrace


# python manage.py migrate
# python3 manage.py runserver_plus --cert-file /tmp/cert.crt 0.0.0.0:8000
while true
do
    python3 manage.py runserver_plus --cert-file /tmp/cert.crt 0.0.0.0:8000
    sleep 1
done
