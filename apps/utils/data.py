from django.contrib.gis.geos import GEOSGeometry


class Bunch(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


ciudades = [
    # ciudad slug: name, osmid
    Bunch({'slug': 'bahia-blanca', 'osm_id': 3302861, 'name': 'Bahía Blanca'}),
    Bunch({'slug': 'buenos-aires', 'osm_id': 3082668, 'name': 'Buenos Aires'}),
    Bunch({'slug': 'cordoba', 'osm_id': 1862787, 'name': 'Córdoba'}),
    Bunch({'slug': 'la-plata', 'osm_id': 2499263, 'name': 'La Plata'}),
    Bunch({'slug': 'mar-del-plata', 'osm_id': 3402727, 'name': 'Mar del Plata'}),
    Bunch({'slug': 'mendoza', 'osm_id': 2204157, 'name': 'Mendoza'}),
    Bunch({'slug': 'rosario', 'osm_id': 3442021, 'name': 'Rosario'}),
    Bunch({'slug': 'salta', 'osm_id': 3059842, 'name': 'Salta'}),
    Bunch({'slug': 'santa-fe', 'osm_id': 3550091, 'name': 'Santa Fe'}),
]

ciudades_es = [
    # ciudad slug: name, osmid
    Bunch({'slug': 'madrid', 'osm_id': 5326784, 'name': 'Madrid'}),
    Bunch({'slug': 'barcelona', 'osm_id': 347950, 'name': 'Barcelona'}),
    Bunch({'slug': 'valencia', 'osm_id': 344953, 'name': 'València'}),
    # Bunch({'slug': 'sevilla', 'osm_id': 342563, 'name': 'Sevilla'}),
    Bunch({'slug': 'bilbao', 'osm_id': 339549, 'name': 'Bilbao'}),
    Bunch({'slug': 'malaga', 'osm_id': 340746, 'name': 'Málaga'}),
]

argentina_simplified = GEOSGeometry('POINT(0 0)')
