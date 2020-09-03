import osmium
import tempfile
from datetime import datetime
from django.contrib.gis.geos import Polygon, MultiPolygon
from django.db import connection
from django.contrib.gis.db.backends.postgis.adapter import PostGISAdapter
from django.contrib.gis.geos.geometry import GEOSGeometry
from apps.catastro.models import AdministrativeArea
from apps.utils.fix_way import fix_polygon


def printfn(str):
    pass

def get_admin_area(inputfile, kid, printfn = printfn):
    _, admin_area = get_admin_areas(datetime.now(), inputfile, 'xx', kid, printfn, True)
    return admin_area

def get_admin_areas(run_timestamp, inputfile, country_code, KING_ID, printfn = printfn, get_only_king = False):

    ADMIN_LEVEL_MIN = 1
    ADMIN_LEVEL_MAX = 8

    KING = None

    admin_areas = [[] for i in range(12)]  # index: admin_level, value
    admin_relations = {}  # index: admin_level, value
    admin_relations_ways_ids = {}
    # this = self

    class RelsHandler(osmium.SimpleHandler):
        def relation(self, r):
            if 'boundary' in r.tags and r.tags['boundary'] == 'administrative' and 'name' in r.tags and 'admin_level' in r.tags and (not get_only_king or r.id == KING_ID):
                ways = []
                for m in r.members:
                    # outer (parts and exclaves) / inner (hole)
                    if m.type == 'w' and m.role in ['outer']:
                        ways.append(m.ref)
                        admin_relations_ways_ids.setdefault(m.ref, []).append(r.id)
                try:
                    admin_level = int(r.tags['admin_level'])
                except ValueError:
                    return
                admin_relations[r.id] = {
                    'import_timestamp': run_timestamp,
                    'osm_id': r.id,
                    'osm_type': 'r',
                    'ways': ways,
                    'admin_level': admin_level,
                    'name': r.tags['name'],  # .encode('utf-8').strip(),
                    'tags': {k:v for k,v in r.tags},
                    'country_code': country_code,
                }
                # this.out2(f"REL {r.id} {r.tags['name'].encode('utf-8').strip()}")

    def make_valid(geom):
        cursor = connection._cursor()
        try:
            try:
                cursor.execute('SELECT ST_MakeValid(%s)', (PostGISAdapter(geom),))
                row = cursor.fetchone()
            except:
                # Responsibility of callers to perform error handling.
                raise
        finally:
            # Close out the connection.  See #9437.
            connection.close()
        return GEOSGeometry(row[0])

    def maybe_make_valid(geom):
        if not geom.valid:
            return make_valid(geom)
        else:
            return geom

    class WaysHandler(osmium.SimpleHandler):
        def way(self, w):

            # ways that are admin areas
            if 'boundary' in w.tags and w.tags['boundary'] == 'administrative' and 'name' in w.tags and 'admin_level' in w.tags:
                linestring = []
                for node in w.nodes:
                    linestring.append([float(node.x) / 10000000, float(node.y) / 10000000])
                if linestring[0][0] == linestring[-1][0] and linestring[0][1] == linestring[-1][1]:
                    admin_level_aux = 0
                    try:
                        admin_level_aux = int(w.tags['admin_level'])
                    except Exception as e:
                        print(f'wrong admin level: {w.tags["admin_level"]}')
                    if admin_level_aux >= ADMIN_LEVEL_MIN and admin_level_aux <= ADMIN_LEVEL_MAX:
                        poly = Polygon(linestring)
                        admin_areas[admin_level_aux].append({
                            'import_timestamp': run_timestamp,
                            'osm_id': w.id,
                            'osm_type': 'w',
                            'geometry': maybe_make_valid(poly),
                            'geometry_simple': maybe_make_valid(poly.simplify(0.001, True)),
                            'admin_level': admin_level_aux,
                            'name': w.tags['name'],  # .encode('utf-8').strip(),
                            'tags': {k:v for k,v in w.tags},
                            'country_code': country_code,
                        })

            # fill relations that are admin areas
            if w.id in admin_relations_ways_ids:
                linestring = []
                for node in w.nodes:
                    linestring.append([float(node.x) / 10000000, float(node.y) / 10000000])

                for rel_id in admin_relations_ways_ids[w.id]:
                    if rel_id in admin_relations and 'ways' in admin_relations[rel_id]:
                        for i, wid in enumerate(admin_relations[rel_id]['ways']):
                            if wid == w.id:
                                admin_relations[rel_id]['ways'][i] = linestring

    printfn(f'Collecting rels, using {inputfile}')
    h = RelsHandler()
    h.apply_file(inputfile)
    printfn('Collecting ways & nodes')
    h = WaysHandler()
    h.apply_file(inputfile, locations=True)

    admin_count_ok = 0
    admin_count_all = 0
    admin_count = 0
    printfn('Joining ways')
    for (k, v) in admin_relations.items():
        admin_count_all = admin_count_all + 1
        dbadminarea = AdministrativeArea.objects.filter(osm_id=v['osm_id'], osm_type=v['osm_type'])
        if dbadminarea:
            dbadminarea = dbadminarea[0]
            v['img_panorama'] = dbadminarea.img_panorama
            v['img_cuadrada'] = dbadminarea.img_cuadrada

        if v['admin_level'] >= ADMIN_LEVEL_MIN and v['admin_level'] <= ADMIN_LEVEL_MAX:
            printfn(f"osmid={k} level={v['admin_level']} name={v['name']}", end="")
            wfull = [w for w in v['ways'] if not isinstance(w, int)]
            if len(wfull) == 0 or float(len(wfull)) / float(len(v['ways'])) < 0.8:
                printfn(f" NOK skipping adminarea, less than 80% of fragments")
                continue
            way, status = fix_polygon(wfull, 1000)
            if way is None:
                # si esta roto, buscar en la base de datos si hay uno con ese id y usar ese way
                printfn(f' ERROR: {status}')
                if dbadminarea:
                    way = dbadminarea.geometry
            else:
                admin_count = admin_count + 1
                printfn(f" OK -> {len(way)}")
                # last point equals first
                admin_count_ok = admin_count_ok + 1
                try:
                    poly = Polygon(way)
                    v['geometry'] = maybe_make_valid(poly)
                    v['geometry_simple'] = maybe_make_valid(poly.simplify(0.01, True))
                    if v['osm_id'] != KING_ID:
                        admin_areas[v['admin_level']].append(v)
                except Exception as e:
                    try:
                        printfn(f" {e}, retrying as multipolygon")
                        mp = []
                        for p in way:
                            p_fixed, status = fix_polygon(p, 1000)
                            if p_fixed:
                                try:
                                    mp.append(Polygon(p_fixed + [p_fixed[0]]))
                                except Exception as e3:
                                    printfn(f" {e3} {status}, skipping fragment. ({len(p_fixed)} nodes) [{status}]")
                        poly = MultiPolygon(mp)
                        v['geometry'] = maybe_make_valid(poly)
                        v['geometry_simple'] = maybe_make_valid(poly.simplify(0.01, True))
                        if v['osm_id'] != KING_ID:
                            admin_areas[v['admin_level']].append(v)
                        printfn('-> ok')
                    except Exception as e2:
                        traceback.print_exc()
                        printfn(f" {e2}, error")
                if v['osm_id'] == KING_ID:
                    KING = v
    printfn(f"TOTALS: all({admin_count_all}) tried({admin_count}) ok({admin_count_ok}), really_ok({len(admin_areas)})")

    return admin_areas, KING


def make_poly_file(mpoly):
    fd, path = tempfile.mkstemp(suffix = '.poly')
    with open(fd, 'w') as file:
        n = 1
        file.write('xxx\n')
        for poly in mpoly:
            for p in poly:
                file.write('%i\n' %(n))
                for node in p:
                    # print(node)
                    file.write('\t%s\t%s\n' %(node[0], node[1]))
                file.write('END\n')
                n = n + 1
    return path
