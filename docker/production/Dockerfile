FROM ubuntu:20.04

ENV TZ Etc/UTC
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

RUN \
    apt-get update \
&& \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-setuptools \
        python3-pip \
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
        libpq-dev \
        osmium-tool \
        gettext \
        osmctools \
&& \
    rm -rf /var/lib/apt/lists/* \
&& \
    pip3 install --upgrade wheel pip \
&& \
    groupadd django && \
    useradd django -s /bin/bash -m -g django -G django

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN \
    pip3 install --no-cache-dir -r /requirements/production.txt \
&& \
    echo "00 2 * * * root /usr/bin/python3 /app/manage.py update_osm --king=argentina --download --admin_areas --update_routes --pois >> /var/log/cualbondi-argentina.log 2>&1" > /etc/cron.d/osm-cualbondi && \
    echo "40 2 * * * root /usr/bin/python3 /app/manage.py update_osm --king=spain --download --admin_areas --update_routes --pois >> /var/log/cualbondi-spain.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "30 3 * * * root /usr/bin/python3 /app/manage.py update_osm --king=ivorycoast --download --admin_areas --update_routes --pois >> /var/log/cualbondi-ivorycoast.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "00 4 * * * root /usr/bin/python3 /app/manage.py update_osm --king=brazil --download --admin_areas --update_routes --pois >> /var/log/cualbondi-brazil.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "30 4 * * * root /usr/bin/python3 /app/manage.py update_osm --king=china --download --admin_areas --update_routes --pois >> /var/log/cualbondi-china.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "30 5 * * * root /usr/bin/python3 /app/manage.py update_osm --king=russia --download --admin_areas --update_routes --pois >> /var/log/cualbondi-russia.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "30 6 * * * root /usr/bin/python3 /app/manage.py update_osm --king=srilanka --download --admin_areas --update_routes --pois >> /var/log/cualbondi-srilanka.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "45 6 * * * root /usr/bin/python3 /app/manage.py update_osm --king=taiwan --download --admin_areas --update_routes --pois >> /var/log/cualbondi-taiwan.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "00 7 * * * root /usr/bin/python3 /app/manage.py update_osm --king=burkinafaso --download --admin_areas --update_routes --pois >> /var/log/cualbondi-burkinafaso.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "00 7 * * * root /usr/bin/python3 /app/manage.py update_osm --king=iran --download --admin_areas --update_routes --pois >> /var/log/cualbondi-iran.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "00 7 * * * root /usr/bin/python3 /app/manage.py update_osm --king=southkorea --download --admin_areas --update_routes --pois >> /var/log/cualbondi-southkorea.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    # echo "10 7 * * * root /usr/bin/python3 /app/manage.py update_osm --king=morocco --download --admin_areas --update_routes --pois >> /var/log/cualbondi-morocco.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "00 4 * * * root /usr/bin/python3 /app/manage.py calcular_envolventes >> /var/log/cualbondi-envolventes.log 2>&1" >> /etc/cron.d/osm-cualbondi && \
    echo "00 5 * * * root /usr/bin/python3 /app/manage.py crear_thumbs -sF >> /var/log/cualbondi-thumbs.log 2>&1" >> /etc/cron.d/osm-cualbondi \
&& \
    chmod 0644 /etc/cron.d/osm-cualbondi

COPY --chown=django ./docker/production/uvicorn.sh ./docker/production/gunicorn.sh ./docker/production/entrypoint.sh ./docker/production/entrypoint+cron.sh /
COPY --chown=django . /app

#USER django

WORKDIR /app

ENTRYPOINT ["/entrypoint+cron.sh"]

EXPOSE 8000
