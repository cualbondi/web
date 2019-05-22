FROM ubuntu:disco

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
    osm2pgsql \
    osmctools \
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
    libpq-dev \
  && rm -rf /var/lib/apt/lists/* \
  && pip3 install wheel

RUN groupadd django \
    && useradd django -s /bin/bash -m -g django -G django

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip3 install --no-cache-dir -r /requirements/production.txt \
    && rm -rf /requirements

RUN echo "04 3 * * * root /usr/bin/python3 /app/manage.py update_osm --update_routes --import_osm --all_arg >> /var/log/cualbondi-update_routes.log 2>&1" > /etc/cron.d/osm-cualbondi
RUN echo "14 3 * * * root /usr/bin/python3 /app/manage.py update_osm --cross --import_osm >> /var/log/cualbondi-cross.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN echo "54 3 * * * root /usr/bin/python3 /app/manage.py update_osm --pois >> /var/log/cualbondi-pois.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN echo "20 4 * * * root /usr/bin/python3 /app/manage.py calcular_envolventes >> /var/log/cualbondi-envolventes.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN echo "30 4 * * * root /usr/bin/python3 /app/manage.py crear_thumbs -sP >> /var/log/cualbondi-thumbs_pois.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN echo "10 5 * * * root /usr/bin/python3 /app/manage.py -f /tmp/part-all.o5m --admin_areas >> /var/log/cualbondi-adminareas.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN echo "30 5 * * * root /usr/bin/python3 /app/manage.py crear_thumbs_catastro -s >> /var/log/cualbondi-thumbs_catastro.log 2>&1" >> /etc/cron.d/osm-cualbondi
RUN chmod 0644 /etc/cron.d/osm-cualbondi

COPY ./docker/production/gunicorn.sh /gunicorn.sh
RUN sed -i 's/\r//' /gunicorn.sh
RUN chmod +x /gunicorn.sh
RUN chown django /gunicorn.sh

COPY ./docker/production/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN chown django /entrypoint.sh

COPY ./docker/production/entrypoint+cron.sh /entrypoint+cron.sh
RUN sed -i 's/\r//' /entrypoint+cron.sh
RUN chmod +x /entrypoint+cron.sh
RUN chown django /entrypoint+cron.sh

COPY . /app

RUN chown -R django /app

#USER django

WORKDIR /app

ENTRYPOINT ["/entrypoint+cron.sh"]

EXPOSE 8000
