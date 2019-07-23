# Cualbondi API version 3

[![Build Status](https://travis-ci.org/cualbondi/web.svg?branch=master)](https://travis-ci.org/cualbondi/web)
[![codecov](https://codecov.io/gh/cualbondi/web/branch/master/graph/badge.svg)](https://codecov.io/gh/cualbondi/web)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/130a1b9f44214a90b4781c9b0b11ba57)](https://www.codacy.com/app/jperelli/web?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=cualbondi/web&amp;utm_campaign=Badge_Grade)
[![Maintainability](https://api.codeclimate.com/v1/badges/b31b447ad26392a9ce15/maintainability)](https://codeclimate.com/github/cualbondi/web/maintainability)

## Common commands

### Run tests locally and clean in one command

    docker-compose -f docker-compose-travis.yml run --rm web python3 manage.py test --noinput; docker-compose -f docker-compose-travis.yml down; docker-compose -f docker-compose-travis.yml rm -f

### Import different parts

```
./manage.py update_osm --king=argentina --download
./manage.py update_osm --king=argentina --admin_areas
./manage.py update_osm --king=argentina --update_routes --add_routes   # for the first time only
./manage.py update_osm --king=argentina --update_routes
./manage.py update_osm --king=argentina --pois
```

### Do it all together for spain

```
./manage.py update_osm --king=argentina --download --admin_areas --update_routes --add_routes --pois
```
