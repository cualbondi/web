FROM python:3

MAINTAINER Cualbondi

ENV PYTHONUNBUFFERED 1

ENV APP_PATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    osm2pgsql \
    osmctools \
    libgeos-dev \
    gdal-bin \
  && rm -rf /var/lib/apt/lists/* \
  && pip install uwsgi

WORKDIR $APP_PATH

COPY requirements.txt $APP_PATH/

RUN pip install -r requirements.txt

COPY . $APP_PATH/

CMD python manage.py collectstatic --noinput && uwsgi --ini /app/uwsgi.ini

EXPOSE 8000