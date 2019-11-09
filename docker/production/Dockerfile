FROM ubuntu:eoan

ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ca-certificates

RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-setuptools \
    python3-pip \
    libgeos-dev \
    gdal-bin \
    libspatialindex-dev \
    postgresql-client \
    libjpeg-dev pngcrush \
    libtiff5-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev google-chrome-stable \
    cron \
    libboost-python-dev \
    libbz2-dev \
    gcc \
    g++ \
    git \
    make \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/* \
  && pip3 install wheel

RUN groupadd django \
    && useradd django -s /bin/bash -m -g django -G django

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip3 install --no-cache-dir -r /requirements/production.txt \
    && rm -rf /requirements

RUN echo "00 2 * * * root /usr/bin/python3 /app/manage.py update_osm --king=argentina --download --admin_areas --update_routes --pois >> /var/log/cualbondi-argentina.log 2>&1" > /etc/cron.d/osm-cualbondi
RUN echo "00 3 * * * root /usr/bin/python3 /app/manage.py update_osm --king=spain --download --admin_areas --update_routes --pois >> /var/log/cualbondi-spain.log 2>&1" > /etc/cron.d/osm-cualbondi
# TODO FIX --cross: RUN echo "00 4 * * * root /usr/bin/python3 /app/manage.py update_osm --king=argentina --cross >> /var/log/cualbondi-cross.log 2>&1" >> /etc/cron.d/osm-cualbondi

RUN echo "00 4 * * * root /usr/bin/python3 /app/manage.py calcular_envolventes >> /var/log/cualbondi-envolventes.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN echo "00 5 * * * root /usr/bin/python3 /app/manage.py crear_thumbs -sP >> /var/log/cualbondi-thumbs_pois.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN echo "00 6 * * * root /usr/bin/python3 /app/manage.py crear_thumbs_catastro -s >> /var/log/cualbondi-thumbs_catastro.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN chmod 0644 /etc/cron.d/osm-cualbondi

COPY --chown=django ./docker/production/uvicorn.sh ./docker/production/gunicorn.sh ./docker/production/entrypoint.sh ./docker/production/entrypoint+cron.sh /
COPY --chown=django . /app

#USER django

WORKDIR /app

ENTRYPOINT ["/entrypoint+cron.sh"]

EXPOSE 8000
