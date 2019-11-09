FROM ubuntu:eoan

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-setuptools \
    python3-pip \
    libgeos-dev \
    gdal-bin \
    libspatialindex-dev \
    postgresql-client \
    libboost-python-dev \
    libbz2-dev \
    zlib1g-dev \
    gcc \
    g++ \
    git \
    make \
  && rm -rf /var/lib/apt/lists/* \
  && pip3 install wheel

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip3 install -r /requirements/local.txt

COPY ./docker/production/entrypoint.sh /entrypoint.sh
COPY ./docker/local/start.sh /start.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
