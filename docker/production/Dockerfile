FROM python:3.6

ENV PYTHONUNBUFFERED 1

RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    osm2pgsql \
    osmctools \
    libgeos-dev \
    gdal-bin \
    libspatialindex-dev \
    postgresql-client \
    libjpeg-dev pngcrush \
    libtiff5-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev google-chrome-stable \
    cron \
  && rm -rf /var/lib/apt/lists/* \
  && pip install uwsgi

RUN groupadd django \
    && useradd django -s /bin/bash -m -g django -G django

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip install --no-cache-dir -r /requirements/production.txt \
    && rm -rf /requirements

RUN echo "54 2 * * * root /usr/local/bin/python /app/manage.py update_osm --update_routes --dry-run --import_osm --all_arg >> /var/log/osm-cualbondi-cron.log 2>&1" > /etc/cron.d/osm-cualbondi
RUN chmod 0644 /etc/cron.d/osm-cualbondi

COPY ./docker/production/gunicorn.sh /gunicorn.sh
RUN sed -i 's/\r//' /gunicorn.sh
RUN chmod +x /gunicorn.sh
RUN chown django /gunicorn.sh

COPY ./docker/production/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN chown django /entrypoint.sh

COPY . /app

RUN chown -R django /app

#USER django

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000
