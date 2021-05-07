#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# put docker's env variables there so that cron can see them
printenv >> /etc/environment

# start cron

# wait until fixing adminareas duplication
# cron

/entrypoint.sh $@
