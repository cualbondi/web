#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


PYTHONPATH=/app jupyter lab /app/notebooks/ --ip 0.0.0.0 --port 8000
