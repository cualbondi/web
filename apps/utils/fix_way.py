from django.contrib.gis.geos import GEOSGeometry, MultiLineString, LineString
import math


def first_pass(ways):
    """
        try to reverse directions in linestrings
        to join segments into a single linestring

        - This is normal in openstreetmap format
        - Also ST_LineMerge() should do this already
    """
    n = len(ways)
    assert n > 1
    ordered_ways = [ways[0]]
    for i in range(1, n):
        way = ways[i]
        prev_way = ordered_ways[-1]
        # if its the first segment on the linestring,
        # try reversing it if it matches with the second
        if ordered_ways[-1] == ways[i-1]:
            if way[0] == prev_way[0] or way[-1] == prev_way[0]:
                ordered_ways[-1] = LineString(prev_way[::-1])
                prev_way = ordered_ways[-1]
        # concat the second segment with the first one
        if prev_way[-1] == way[0]:
            ordered_ways[-1] += way[1:]
        # concat the second segment reversing it
        elif prev_way[-1] == way[-1]:
            ordered_ways[-1] += way[::-1][1:]
        # can not form a single linestring, continue processing
        else:
            ordered_ways.append(way)

    if len(ordered_ways) == 1:
        return ordered_ways[0]
    return MultiLineString(ordered_ways)


def sort_ways(ways):
    """
        move ways from one place to another to get the closest ones together
        the first one is taken as important (the one that sets the direction)
        Also joins the way if extreme points are the same

        - This is not "expected" by osm. We are trying to fix the way now
        - Nevertheless I think this is also done by ST_LineMerge()
    """
    ws = ways[:]
    sorted_ways = [ws[0]]
    ws = ws[1:]
    while len(ws) > 0:
        ws = sorted(ws, key=lambda w: w.distance(sorted_ways[-1]))
        sorted_ways.append(ws[0])
        ws = ws[1:]
    ret_ways = first_pass(sorted_ways)
    # print('SORTED {} -> {}'.format(len(ways), len(ret_ways)))
    return ret_ways


def dist_haversine(P1, P2):
    lon1, lat1 = P1
    lon2, lat2 = P2
    radius = 6371000  # meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c
    return d


def join_ways(ways, tolerance):
    """
        Join adjacent ways that have their extreme points
        closer than <tolerance> in meters

        - This is not "expected". We are trying to fix the way now
        - This is not done by ST_LineMerge()
        - I'm not sure if this conserves the direction from first to last
    """
    joined = [ways[0]]
    # print([[p for p in l] for l in ways[1:]])
    for w in ways[1:]:
        # print(joined[-1][-1], w[0])
        # print(dist_haversine(joined[-1][-1], w[0]))
        # print(joined[-1][-1], w[-1])
        # print(dist_haversine(joined[-1][-1], w[-1]))
        if dist_haversine(joined[-1][-1], w[0]) < tolerance:
            # print('1.last + 2.first')
            joined[-1] += w
        else:
            if dist_haversine(joined[-1][-1], w[-1]) < tolerance:
                # print('1.last + 2.last')
                joined[-1] += LineString(w[::-1])
            else:
                if dist_haversine(joined[-1][0], w[0]) < tolerance:
                    # print('1.first + 2.first')
                    joined[-1] = LineString(joined[-1][::-1])
                    joined[-1] += w
                else:
                    if dist_haversine(joined[-1][0], w[-1]) < tolerance:
                        # print('1.first + 2.last')
                        joined[-1] = LineString(joined[-1][::-1])
                        joined[-1] += LineString(w[::-1])
                    else:
                        # print('1.split.2')
                        joined.append(w)
    if len(joined) == 1:
        return joined[0]
    return sort_ways(joined)


def fix_way(way, tolerance=0):
    """ tries to sort and fix the way into a linestring """
    way = GEOSGeometry(way)
    if way.geom_type == 'LineString':
        return way, '0: ok'
    if way.geom_type == 'MultiLineString':
        way = first_pass(way)
        if way.geom_type == 'LineString':
            # print('SAFE first_pass!')
            return way, '1: ok, first_pass'
        way = sort_ways(way)
        if way.geom_type == 'LineString':
            # print('SAFE sorted!')
            return way, '2: broken, sort'
        if tolerance > 0:
            way = join_ways(way, tolerance)
            if way.geom_type == 'LineString':
                # print('SAFE tolerance!')
                return way, '3: broken, tolerance'
        # print(len(way))
        # print(way.ewkt)

    return None, '4: broken'
