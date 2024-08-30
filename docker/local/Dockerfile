FROM ubuntu:24.04

ENV TZ Etc/UTC \
  PYTHONUNBUFFERED 1 \
  DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-setuptools \
    python3-pip \
    python3-venv \
    libgeos-dev \
    gdal-bin \
    libspatialindex-dev \
    postgresql-client \
    cron \
    libboost-python-dev \
    libbz2-dev \
    gcc \
    g++ \
    git \
    make \
    osmium-tool \
    gettext \
    osmctools \
    cargo \
  && rm -rf /var/lib/apt/lists/* \
  && python3 -m venv /venv \
  && /venv/bin/pip install --upgrade wheel pip

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN /venv/bin/pip install --no-cache-dir -r /requirements/local.txt

COPY ./docker/production/entrypoint.sh /entrypoint.sh
COPY ./docker/local/start.sh /start.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
