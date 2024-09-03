FROM postgres:16

MAINTAINER Cualbondi

ENV POSTGIS_VERSION=3

# Update repositories & Install dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-16-postgis-${POSTGIS_VERSION} \
        postgresql-16-postgis-${POSTGIS_VERSION}-scripts \
    && rm -rf /var/lib/apt/lists/*

COPY import-sql.sh import-sql.sh
COPY export-sql.sh export-sql.sh
