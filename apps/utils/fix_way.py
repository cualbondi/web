from django.contrib.gis.geos import GEOSGeometry, MultiLineString, LineString
import math

point_names = {
    (-57.93176591794997, -34.92797747797999): "1",
    (-57.93880403440505, -34.92248841780390): "2",
    (-57.94996202390700, -34.91474681147465): "3",
    (-57.96180665891677, -34.90587825610113): "4",
    (-57.97056138914138, -34.89968377625544): "5",
    (-57.97141969602614, -34.89901502605655): "6",
    (-57.97828971360718, -34.89309542071704): "7",
    (-57.98961936448609, -34.88549185620056): "8"
}


def stringify(mls):
    if isinstance(mls, str):
        mls = GEOSGeometry(mls)
    ans = ''
    if mls.geom_type == 'MultiLineString':
        for ls in mls:
            for point in ls:
                ans += point_names[point] + ' '
            ans += '- '
        ans = ans[:-2]
    if mls.geom_type == 'LineString':
        for point in mls:
            ans += point_names[point] + ' '
    return ans

def first_pass(ways):
    """ try to reverse directions in linestrings to join segments into a single linestring """
    n = len(ways)
    assert n > 1
    ordered_ways = [ways[0]]
    for i in range(1, n):
        way = ways[i]
        prev_way = ordered_ways[-1]
        # if its the first segment on the linestring, try reversing it if it matches with the second
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
    """move ways from one place to another to get the closest ones together"""
    ws = ways[:]
    sorted_ways = [ws[0]]
    ws = ws[1:]
    while len(ws) > 0:
        ws = sorted(ws, key=lambda w: w.distance(sorted_ways[-1]))
        sorted_ways.append(ws[0])
        ws = ws[1:]
    ret_ways = first_pass(sorted_ways)
    return ret_ways


def dist(P1, P2):
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
    """join adjacent ways that are closer than <tolerance> meters"""
    joined = [ways[0]]
    for w in ways:
        if dist(joined[-1][-1], w[0]) < tolerance:
            joined[-1] += w
        else:
            if dist(joined[-1][-1], w[-1]) < tolerance:
                joined[-1] += LineString(w[::-1])
            else:
                joined.append(w)
    if len(joined) == 1:
        return joined[0]
    return sort_ways(joined)


def fix_way(way, tolerance):
    """ tries to sort and fix the way into a linestring """
    way = GEOSGeometry(way)
    if way.geom_type == 'LineString':
        return way
    if way.geom_type == 'MultiLineString':
        way = first_pass(way)
        if way.geom_type == 'LineString':
            return way
        way = sort_ways(way)
        if way.geom_type == 'LineString':
            print('SAFE sorted!')
            return way
        way = join_ways(way, tolerance)
        if way.geom_type == 'LineString':
            print('SAFE tolerance!')
            return way

    return None
