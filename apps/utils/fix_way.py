from django.contrib.gis.geos import GEOSGeometry, MultiLineString, LineString


def first_pass(ways):
    """ try to reverse directions in linestrings to join segments into a single linestring """
    n = len(ways)
    ordered_ways = [ways[0]]
    for i in range(1, n):
        way = ways[i]
        prev_way = ways[i-1]
        # if its the first segment on the linestring, try reversing it if it matches with the second
        if ordered_ways[-1] == prev_way:
            if way[0] == prev_way[0] or way[-1] == prev_way[0]:
                ordered_ways[-1] == LineString(prev_way[::-1])
        # concat the second segment with the first one
        if prev_way[-1] == way[0]:
            ordered_ways[-1] += way[1:]
        # concant the second segment reversing it
        elif prev_way[-1] == way[-1]:
            ordered_ways[-1] += way[::-1][1:]
        # can not form a single linestring, continue processing
        else:
            ordered_ways.append(way)

    if len(ordered_ways) == 1:
        return ordered_ways[0]
    return MultiLineString(ordered_ways)


def fix_way(way):
    way = GEOSGeometry(way)
    if way.geom_type == 'LineString':
        return way
    if way.geom_type == 'MultiLineString':
        first_pass(way)

    return None
