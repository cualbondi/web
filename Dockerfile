FROM python:3

MAINTAINER Cualbondi

ENV PYTHONUNBUFFERED 1

ENV APP_PATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    osm2pgsql \
    osmctools \
    libgeos-dev \
    gdal-bin \
    libjpeg-dev \
    libtiff5-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev \
    pngcrush \
  && rm -rf /var/lib/apt/lists/* \
  && pip install uwsgi

# Install Google Chrome
RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get -yqq update && \
    apt-get -yqq install google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

WORKDIR $APP_PATH

COPY requirements.txt $APP_PATH/

RUN pip install -r requirements.txt

COPY . $APP_PATH/

CMD python manage.py collectstatic --noinput && uwsgi --ini /app/uwsgi.ini

EXPOSE 8000