FROM ubuntu:disco

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-setuptools \
    python3-pip \
    osm2pgsql \
    osmctools \
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
    osmium-tool \
  && rm -rf /var/lib/apt/lists/* \
  && pip3 install wheel

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip3 install -r /requirements/local.txt

COPY ./docker/production/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./docker/local/start.sh /start.sh
RUN sed -i 's/\r//' /start.sh
RUN chmod +x /start.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
