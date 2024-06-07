FROM postgres:14

MAINTAINER Cualbondi

ENV POSTGIS_VERSION=3

# Update repositories & Install dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-14-postgis-${POSTGIS_VERSION} \
        postgresql-14-postgis-${POSTGIS_VERSION}-scripts \
    && rm -rf /var/lib/apt/lists/*

COPY import-sql.sh import-sql.sh
COPY export-sql.sh export-sql.sh
