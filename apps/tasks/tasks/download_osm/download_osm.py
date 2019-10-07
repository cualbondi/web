from prefect import Flow
from .download_pbf import download_pbf
from .admin_areas import admin_areas

king = {
    'name': 'argentina',
    'url': 'http://download.geofabrik.de/south-america/argentina-latest.osm.pbf',
    'id': 286393,
    'paradas_completas': False,
}


with Flow("download-osm") as flow:
    download_pbf(king)
    admin_areas(upstream_tasks=[download_pbf])

