from django.contrib.gis.geos import GEOSGeometry, MultiLineString, LineString, Point
from functools import lru_cache
import math


def first_pass(ways):
    """
        try to reverse directions in linestrings
        to join segments into a single linestring

        - This is normal in openstreetmap format
        - Also ST_LineMerge() should do this already
    """
    n = len(ways)
    ordered_ways = [ways[0][:]]
    for i in range(1, n):
        # print(f'{i},', end='')
        way = ways[i][:]
        prev_way = ordered_ways[-1][:]
        # if its the first segment on the linestring,
        # try reversing it if it matches with the second
        if ordered_ways[-1] == ways[i-1]:
            if way[0] == prev_way[0] or way[-1] == prev_way[0]:
                ordered_ways[-1] = prev_way[::-1]
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
    return ordered_ways


@lru_cache(maxsize=2**20)
def pointdistance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    # return Point(p1).distance(Point(p2))


def edgedistance(w1, w2):
    w1p1 = tuple(w1[0])
    w1p2 = tuple(w1[-1])
    w2p1 = tuple(w2[0])
    w2p2 = tuple(w2[-1])
    return min(
        pointdistance(w1p1, w2p1),
        pointdistance(w1p2, w2p2),
        pointdistance(w1p1, w2p2),
        pointdistance(w1p2, w2p1),
    )

# import cProfile

# def profileit(func):
#     def wrapper(*args, **kwargs):
#         datafn = func.__name__ + ".profile"  # Name the data file sensibly
#         prof = cProfile.Profile()
#         retval = prof.runcall(func, *args, **kwargs)
#         prof.dump_stats(datafn)
#         return retval

#     return wrapper

# @profileit
def sort_ways(ways):
    """
        move ways from one place to another to get the closest ones together
        the first one is taken as important (the one that sets the direction)
        Also joins the way if extreme points are the same

        - This is not "expected" by osm. We are trying to fix the way now
        - Nevertheless I think this is also done by ST_LineMerge()
    """

    # def sort_function(first, w):
    #     d = w.distance(first)
    #     count_touches = 4
    #     if (first[0] == w[0]):
    #         count_touches -= 1
    #     if (first[-1] == w[0]):
    #         count_touches -= 1
    #     if (first[0] == w[-1]):
    #         count_touches -= 1
    #     if (first[-1] == w[-1]):
    #         count_touches -= 1
    #     return d + count_touches
    # from timeit import default_timer as timer
    # t1 = timer()
    ws = ways[:]
    # ws = [w if isinstance(w, LineString) else LineString(w) for w in ways[:]]
    sorted_ways = [ws[0]]
    ws = ws[1:]
    while len(ws) > 0:
        # print(f'{len(ws)}')
        # print(pointdistance.cache_info())
        # ws = sorted(ws, key=lambda w: sort_function(sorted_ways[-1], w))
        # ws = sorted(ws, key=lambda w: edgedistance(w, sorted_ways[-1]))
        mindist = float('Inf')
        minidx = None
        for i in range(0, len(ws)):
            w = ws[i]
            dist = edgedistance(w, sorted_ways[-1])
            if dist < mindist:
                mindist = dist
                minidx = i

        sorted_ways.append(ws[minidx])
        ws.pop(minidx)

        # print(pointdistance.cache_info())
    # 30.82882612600224

    # t2 = timer()
    # print(f'time: {t2-t1}')

    sorted_ways = [[list(n) for n in w] for w in sorted_ways]

    if len(sorted_ways) == 1:
        return sorted_ways[0]
    return sorted_ways
    # print('SORTED {} -> {}'.format(len(ways), len(ret_ways)))


def dist_haversine(P1, P2):

    # this is so the function can work with all following formats
    # [-64.1941384, -31.4469149]
    # [-641941384.0, -314469149.0]
    # [-641941384, -314469149]
    if (P1[0] % 1 == 0 and P2[1] % 1 == 0):
        lon1, lat1 = (P1[0]/10000000, P1[1]/10000000)
        lon2, lat2 = (P2[0]/10000000, P2[1]/10000000)
    else:
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
    joined = [ways[0][:]]
    # print([[p for p in l] for l in ways[1:]])
    for w in ways[1:]:
        # print(joined[-1][-1], w[0])
        # print(dist_haversine(joined[-1][-1], w[0]))
        # print(joined[-1][-1], w[-1])
        # print(dist_haversine(joined[-1][-1], w[-1]))
        if dist_haversine(joined[-1][-1], w[0]) < tolerance:
            # print('1.last + 2.first')
            joined[-1] += w[:]
        else:
            if dist_haversine(joined[-1][-1], w[-1]) < tolerance:
                # print('1.last + 2.last')
                joined[-1] += w[::-1]
            else:
                if dist_haversine(joined[-1][0], w[0]) < tolerance:
                    # print('1.first + 2.first')
                    joined[-1] = joined[-1][::-1]
                    joined[-1] += w[:]
                else:
                    if dist_haversine(joined[-1][0], w[-1]) < tolerance:
                        # print('1.first + 2.last')
                        joined[-1] = joined[-1][::-1]
                        joined[-1] += w[::-1]
                    else:
                        # print('1.split.2')
                        joined.append(w[:])
    if len(joined) == 1:
        return joined[0]
    return joined


def isLineString(way):
    # print(way)
    # print(way[0][0])
    return isinstance(way[0][0], (int, float))


def isMultiLineString(way):
    return isinstance(way[0][0][0], (int, float))


def isClosedMultiPolygon(way):
    isClosed = True
    for w in way:
        isClosed = isClosed and (isinstance(w[0], (int, float)) or (
            isinstance(w[0][0], (int, float)) and
            w[0][0] == w[-1][0] and
            w[0][1] == w[-1][1]
        ))
    return isClosed


def isOpenMultiPolygon(way):
    return not isClosedMultiPolygon(way)


def fix_polygon(way, tolerance=0):
    """ tries to sort and fix the polygon into a closed multipolygon """

    try:

        if len(way) == 0:
            return None, '5: broken, empty'
        if isClosedMultiPolygon(way):
            return way, '0: ok'
        if isOpenMultiPolygon(way):
            passed = first_pass(way[:])
            if isClosedMultiPolygon(passed):
                # print('SAFE first_pass!')
                return passed, '1: ok, first_pass'
            sorted = sort_ways(passed)
            sorted_passed = first_pass(sorted)
            if isClosedMultiPolygon(sorted_passed):
                # print('SAFE sorted!')
                return sorted_passed, '2: broken, sort'
            if tolerance > 0:
                tolerated_sorted = join_ways(sorted, tolerance)
                if isClosedMultiPolygon(tolerated_sorted):
                    # print('SAFE tolerance!')
                    return tolerated_sorted, '3b: broken, sort + tolerance'

            # print(len(way))
            # print(way.ewkt)

        return None, '4: broken'

    except Exception as e:
        # import traceback
        # traceback.print_exc()
        return None, '9: ERROR PROCESSING: {}'.format(str(e))


def fix_way(way, tolerance=0):
    """ tries to sort and fix the way into a linestring """

    try:

        if len(way) == 0:
            return None, '5: broken, empty'
        if isLineString(way):
            return way, '0: ok'
        if isMultiLineString(way):
            passed = first_pass(way[:])
            if isLineString(passed):
                # print('SAFE first_pass!')
                return passed, '1: ok, first_pass'
            sorted = sort_ways(way)
            sorted_passed = first_pass(sorted)
            if isLineString(sorted_passed):
                # print('SAFE sorted!')
                return sorted_passed, '2: broken, sort'
            if tolerance > 0:
                tolerated = join_ways(way, tolerance)
                if isLineString(tolerated):
                    # print('SAFE tolerance!')
                    return tolerated, '3: broken, tolerance'
            if tolerance > 0:
                tolerated_sorted = join_ways(sorted, tolerance)
                if isLineString(tolerated_sorted):
                    # print('SAFE tolerance!')
                    return tolerated_sorted, '3b: broken, sort + tolerance'

            # print(len(way))
            # print(way.ewkt)

        return None, '4: broken'

    except Exception as e:
        return None, '9: ERROR PROCESSING: {}'.format(str(e))
