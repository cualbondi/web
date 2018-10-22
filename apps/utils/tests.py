from .fix_way import fix_way
from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry


POSITIVE = """
    LINESTRING(
        -57.94253110905379 -34.92025019346214,
        -57.94656515141219 -34.91708317458055,
        -57.95085668583601 -34.91370488641156,

        -57.95126438160628 -34.91344151465948,
        -57.95448303242415 -34.91115404576736,
        -57.95903841604024 -34.90798275551346,
        -57.96418825734884 -34.90446331221241,
        -57.96805063833028 -34.90101411142836,

        -57.96861672351383 -34.90035341073901,
        -57.97273013995749 -34.89627304611792,
        -57.97787998126608 -34.89317550236659,
        -57.98337314532858 -34.88993703629123
    )
"""

POSITIVE = ' '.join(POSITIVE.split())

PASS_CASES = [

    # 0 same linestring
    """
        LINESTRING(
            -57.94253110905379 -34.92025019346214,
            -57.94656515141219 -34.91708317458055,
            -57.95085668583601 -34.91370488641156,

            -57.95126438160628 -34.91344151465948,
            -57.95448303242415 -34.91115404576736,
            -57.95903841604024 -34.90798275551346,
            -57.96418825734884 -34.90446331221241,
            -57.96805063833028 -34.90101411142836,

            -57.96861672351383 -34.90035341073901,
            -57.97273013995749 -34.89627304611792,
            -57.97787998126608 -34.89317550236659,
            -57.98337314532858 -34.88993703629123
        )
    """,

    # 1 JOINED (1 2 3 - 3 4 5 6 7 8 9 10 11 12)
    """
        MULTILINESTRING(
            (
                -57.94253110905379 -34.92025019346214,
                -57.94656515141219 -34.91708317458055,
                -57.95085668583601 -34.91370488641156
            ),
            (
                -57.95085668583601 -34.91370488641156,
                -57.95126438160628 -34.91344151465948,
                -57.95448303242415 -34.91115404576736,
                -57.95903841604024 -34.90798275551346,
                -57.96418825734884 -34.90446331221241,
                -57.96805063833028 -34.90101411142836,

                -57.96861672351383 -34.90035341073901,
                -57.97273013995749 -34.89627304611792,
                -57.97787998126608 -34.89317550236659,
                -57.98337314532858 -34.88993703629123
            )
        )
    """,

    # 2 JOINED REVERSED (1 2 3 - 12 11 10 9 8 7 6 5 4 3)
    """
        MULTILINESTRING(
            (
                -57.94253110905379 -34.92025019346214,
                -57.94656515141219 -34.91708317458055,
                -57.95085668583601 -34.91370488641156
            ),
            (
                -57.98337314532858 -34.88993703629123,
                -57.97787998126608 -34.89317550236659,
                -57.97273013995749 -34.89627304611792,
                -57.96861672351383 -34.90035341073901,
                -57.96805063833028 -34.90101411142836,
                -57.96418825734884 -34.90446331221241,
                -57.95903841604024 -34.90798275551346,
                -57.95448303242415 -34.91115404576736,
                -57.95126438160628 -34.91344151465948,
                -57.95085668583601 -34.91370488641156
            )
        )
    """,

    # 3 JOINED ALL REVERSED (3 2 1 - 7 6 5 4 3 - 12 11 10 9 8 7)
    """
        MULTILINESTRING(
            (
                -57.95085668583601 -34.91370488641156,
                -57.94656515141219 -34.91708317458055,
                -57.94253110905379 -34.92025019346214
            ),
            (
                -57.96805063833028 -34.90101411142836,
                -57.96418825734884 -34.90446331221241,
                -57.95903841604024 -34.90798275551346,
                -57.95448303242415 -34.91115404576736,
                -57.95126438160628 -34.91344151465948,
                -57.95085668583601 -34.91370488641156
            ),
            (
                -57.98337314532858 -34.88993703629123,
                -57.97787998126608 -34.89317550236659,
                -57.97273013995749 -34.89627304611792,
                -57.96861672351383 -34.90035341073901,
                -57.96805063833028 -34.90101411142836
            )
        )
    """,

    # 4 GAP 100 meters (1 2 3 - 4 5 6 7 8 - 9 10 11 12)
    """
        MULTILINESTRING(
            (
                -57.94253110905379 -34.92025019346214,
                -57.94656515141219 -34.91708317458055,
                -57.95085668583601 -34.91370488641156
            ),
            (
                -57.95126438160628 -34.91344151465948,
                -57.95448303242415 -34.91115404576736,
                -57.95903841604024 -34.90798275551346,
                -57.96418825734884 -34.90446331221241,
                -57.96805063833028 -34.90101411142836
            ),
            (
                -57.96861672351383 -34.90035341073901,
                -57.97273013995749 -34.89627304611792,
                -57.97787998126608 -34.89317550236659,
                -57.98337314532858 -34.88993703629123
            )
        )
    """,

    # 5 GAP 100 meters reversed (3 2 1 - 8 7 6 5 4 - 12 11 10 9)
    """
        MULTILINESTRING(
            (
                -57.95085668583601 -34.91370488641156,
                -57.94656515141219 -34.91708317458055,
                -57.94253110905379 -34.92025019346214
            ),
            (
                -57.96805063833028 -34.90101411142836,
                -57.96418825734884 -34.90446331221241,
                -57.95903841604024 -34.90798275551346,
                -57.95448303242415 -34.91115404576736,
                -57.95126438160628 -34.91344151465948
            ),
            (
                -57.98337314532858 -34.88993703629123,
                -57.97787998126608 -34.89317550236659,
                -57.97273013995749 -34.89627304611792,
                -57.96861672351383 -34.90035341073901
            )
        )
    """,

    # 6 joined unsorted (1 2 3 - 7 8 9 10 11 12 - 3 4 5 6 7)
    """
        MULTILINESTRING(
            (
                -57.94253110905379 -34.92025019346214,
                -57.94656515141219 -34.91708317458055,
                -57.95085668583601 -34.91370488641156
            ),
            (
                -57.96805063833028 -34.90101411142836,
                -57.96861672351383 -34.90035341073901,
                -57.97273013995749 -34.89627304611792,
                -57.97787998126608 -34.89317550236659,
                -57.98337314532858 -34.88993703629123
            ),
            (
                -57.95085668583601 -34.91370488641156,
                -57.95126438160628 -34.91344151465948,
                -57.95448303242415 -34.91115404576736,
                -57.95903841604024 -34.90798275551346,
                -57.96418825734884 -34.90446331221241,
                -57.96805063833028 -34.90101411142836
            )
        )
    """,

    # 7 GAP 100 meters unsorted (1 2 3 - 8 9 10 11 12 - 4 5 6 7)
    """
        MULTILINESTRING(
            (
                -57.94253110905379 -34.92025019346214,
                -57.94656515141219 -34.91708317458055,
                -57.95085668583601 -34.91370488641156
            ),
            (
                -57.96861672351383 -34.90035341073901,
                -57.97273013995749 -34.89627304611792,
                -57.97787998126608 -34.89317550236659,
                -57.98337314532858 -34.88993703629123
            ),
            (
                -57.95126438160628 -34.91344151465948,
                -57.95448303242415 -34.91115404576736,
                -57.95903841604024 -34.90798275551346,
                -57.96418825734884 -34.90446331221241,
                -57.96805063833028 -34.90101411142836
            )
        )
    """,

    # 8 GAP 100 meters unsorted  reverse (3 2 1 - 12 11 10 9 8 - 7 6 5 4)
    """
        MULTILINESTRING(
            (
                -57.95085668583601 -34.91370488641156,
                -57.94656515141219 -34.91708317458055,
                -57.94253110905379 -34.92025019346214
            ),
            (
                -57.98337314532858 -34.88993703629123,
                -57.97787998126608 -34.89317550236659,
                -57.97273013995749 -34.89627304611792,
                -57.96861672351383 -34.90035341073901
            ),
            (
                -57.96805063833028 -34.90101411142836,
                -57.96418825734884 -34.90446331221241,
                -57.95903841604024 -34.90798275551346,
                -57.95448303242415 -34.91115404576736,
                -57.95126438160628 -34.91344151465948
            )
        )
    """
]

NOT_PASS_CASES = [
    # GAP 1000 meters (6 7 8 - 1 2 3 4)
    """
        MULTILINESTRING(
            (
                -57.97141969602614 -34.89901502605655,
                -57.97828971360718 -34.89309542071704,
                -57.98961936448609 -34.88549185620056
            ),
            (
                -57.93176591794997 -34.92797747797999,
                -57.93880403440505 -34.92248841780390,
                -57.94996202390700 -34.91474681147465,
                -57.96180665891677 -34.90587825610113
            )
        )
    """,

    # GAP 1000 meters reversed (1 2 3 4 - 6 7 8)
    """
        MULTILINESTRING(
            (
                -57.93176591794997 -34.92797747797999,
                -57.93880403440505 -34.92248841780390,
                -57.94996202390700 -34.91474681147465,
                -57.96180665891677 -34.90587825610113
            ),
            (
                -57.97141969602614 -34.89901502605655,
                -57.97828971360718 -34.89309542071704,
                -57.98961936448609 -34.88549185620056
            )
        )
    """,
]

for i, case in enumerate(PASS_CASES):
    PASS_CASES[i] = ' '.join(case.split())

for i, case in enumerate(NOT_PASS_CASES):
    NOT_PASS_CASES[i] = ' '.join(case.split())

TOLERANCE = 150

point_names = {
    (-57.94253110905379, -34.92025019346214): "1",
    (-57.94656515141219, -34.91708317458055): "2",
    (-57.95085668583601, -34.91370488641156): "3",

    (-57.95126438160628, -34.91344151465948): "4",
    (-57.95448303242415, -34.91115404576736): "5",
    (-57.95903841604024, -34.90798275551346): "6",
    (-57.96418825734884, -34.90446331221241): "7",
    (-57.96805063833028, -34.90101411142836): "8",

    (-57.96861672351383, -34.90035341073901): "9",
    (-57.97273013995749, -34.89627304611792): "10",
    (-57.97787998126608, -34.89317550236659): "11",
    (-57.98337314532858, -34.88993703629123): "12"
}


def stringify(mls):
    if mls is None:
        return None
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


class FixWayTestCase(TestCase):

    def test_fix_ways(self):
        """Fix all positive ways"""
        positive = GEOSGeometry(POSITIVE)
        i = 0
        for case in PASS_CASES:
            fixed = fix_way(case, TOLERANCE)
            # print('case # ', i)
            # print('before fix: ', stringify(case))
            # print('after fix: ', stringify(fixed))
            self.assertSequenceEqual(fixed, positive, msg='[#{}] {}'.format(i, case))
            i += 1

    def test_not_fix_ways(self):
        """Won't fix negative ways"""
        for case in NOT_PASS_CASES:
            self.assertIsNone(fix_way(case, TOLERANCE))