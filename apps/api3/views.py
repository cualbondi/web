from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from rest_framework import exceptions
from rest_framework import pagination
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework.mixins import UpdateModelMixin

from apps.catastro.models import Ciudad, PuntoBusqueda
from apps.core.models import Linea, Recorrido, ImporterLog
from . import serializers


class CiudadesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.CiudadSerializer
    queryset = Ciudad.objects.all()


class LineasViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.LineaSerializerFull
    queryset = Linea.objects.all()


class CBPagination(pagination.PageNumberPagination):
    page_size = 5

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'page': self.page.number,
            'page_size': self.page.paginator.per_page,
            'page_count': self.page.paginator.num_pages,
            'results': data
        })


class IsStaffOrReadOnly(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """

    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_staff
        )


class RecorridosViewSet(viewsets.GenericViewSet, UpdateModelMixin):
    """
        Parametros querystring

         - `l` lista de puntos (lon,lat floats) y radio (int: metros) en orden
            por los cuales se busca que pase una ruta. Ejemplos a continuación:

            - `l=55.3324,-55.4433,200`
            - `l=55.3324,-55.4433,200|55.1112,-55.3334,300`
            - [live example](/api/recorridos/?l=-57.957258224487305,-34.92056351681724,200|-57.94755935668945,-34.92556010123052,200)

         - `t` true/false: buscar con transbordo (true). `false` por defecto.


         - `q` string: para búsqueda por nombre de recorrido (fuzzy search)
         - `l` punto (lon,lat floats) y radio (int: metros)

            - `q=129&l=55.3324,-55.4433,200`
    """

    serializer_class = serializers.RecorridoPureModelSerializer
    queryset = Recorrido.objects.all()
    pagination_class = CBPagination
    permission_classes = [IsStaffOrReadOnly]

    def list(self, request):
        q = request.query_params.get('q', None)
        l = request.query_params.get('l', None)
        t = request.query_params.get('t', 'false')

        if t == 'true':
            t = True
        elif t == 'false':
            t = False
        else:
            raise exceptions.ValidationError(
                {'detail': '\'t\' parameter malformed: Expected \'true\' or \'false\''}
            )

        if q is None:
            try:
                lp = []  # lista de puntos
                for p in l.split('|'):
                    ps = p.split(',')
                    lp.append({'p': GEOSGeometry('POINT({} {})'.format(ps[0], ps[1]), srid=4326), 'r': int(ps[2])})
            except Exception:
                raise exceptions.ValidationError(
                    {'detail': '\'l\' parameter malformed'}
                )
            if len(lp) > 2:
                raise exceptions.ValidationError(
                    {'detail': '\'l\' parameter accepts up to 2 points max.'}
                )

            if len(lp) == 1:
                qs = Recorrido.objects.filter(ruta__distance_lte=(lp[0]['p'], D(m=lp[0]['r'])))
                page = self.paginate_queryset(qs)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    return self.get_paginated_response(serializer.data)
                else:
                    return Response([])

            if not t:
                # sin transbordo
                routerResults = Recorrido.objects.get_recorridos(lp[0]['p'], lp[1]['p'], lp[0]['r'], lp[1]['r'])
            else:
                # con transbordo
                # routerResults = Recorrido.objects.get_recorridos_combinados_sin_paradas(lp[0]['p'], lp[1]['p'], lp[0]['r'], lp[1]['r'], 500)
                routerResults = Recorrido.objects.get_recorridos_combinados(lp[0]['p'], lp[1]['p'], lp[0]['r'], lp[1]['r'], 500)

            page = self.paginate_queryset(routerResults)
            if page is not None:
                ser = serializers.RouterResultSerializer(page, many=True)
                return self.get_paginated_response(ser.data)
            else:
                return Response([])

        if q is not None:
            if l is None:
                raise exceptions.ValidationError(
                    {'detail': '\'l\' parameter is required when using `q` parameter'}
                )
            p = l.split(',')
            try:
                r = int(p[2])
            except Exception:
                r = 10000
            p = GEOSGeometry('POINT({} {})'.format(p[0], p[1]), srid=4326)
            page = self.paginate_queryset(list(
                Recorrido.objects.fuzzy_like_trgm_query(q, p, r)
            ))
            if page is not None:
                serializer = serializers.RecorridoCustomSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            else:
                return Response([])


class GeocoderViewSet(viewsets.GenericViewSet):
    """
        Parámetros querystring

         - `q` obligatorio: string a geobuscar
         - `mk` opcional (arcgis): arcgis `magic key` si viene del suggest
         - `c` opcional: slug de la ciudad donde buscar

        Busca el valor del parámetro `q`
        usando varias fuentes según el formato del string de búsqueda

         - **Geocoder** [Google]
            - [12 1234](/api//geocoder/?q=12%201234&c=la-plata)
            - [12 n 1234](/api//geocoder/?q=12%20n%201234&c=la-plata)
            - [centenario 1234](/api//geocoder/?q=centenario%20n%201234&c=la-plata))
         - **Intersección de calles** [OSM]
            - [12 y 62](/api//geocoder/?q=12%20y%2062&c=la-plata)
            - perón y alvarez
         - **POI (Point Of Interest)** [OSM y Cualbondi]
            - plaza rocha
            - hospital
         - **Zona (Barrio / Ciudad)** [Cualbondi] (devuelve geocentro)
            - berisso
            - colegiales

        El geocoder usa varias fuentes y técnicas, entre ellas fuzzy search.
        Por esto, devuelve un valor de "precision" para cada registro.

        Utiliza el parámetro `c` (ciudad) para dar mas contexto al lugar
        donde se está buscando. Esto ayuda a evitar ambigüedad en la búsqueda
        ya que puede haber dos calles que se llamen igual en distintas ciudades
        pero no restringe la búsqueda a esa ciudad (sólo altera la precisión)
    """
    serializer_class = serializers.GeocoderSerializer
    queryset = ''

    def list(self, request):
        q = request.query_params.get('q', None)
        c = request.query_params.get('c', None)
        # mk = request.query_params.get('mk', None)
        if not q:
            raise exceptions.ValidationError(
                {'detail': 'expected \'q\' parameter'}
            )
        else:
            try:
                res = PuntoBusqueda.objects.geocode(q, c)
                ser = self.get_serializer(res, many=True)
                return Response(ser.data)
            except ObjectDoesNotExist:
                return Response([])


class GeocoderSuggestViewSet(viewsets.GenericViewSet):
    """
        Parámetros querystring

         - `q` obligatorio: string a geobuscar
         - `c` opcional: slug de la ciudad donde buscar

        Busca el valor del parámetro `q`
        usando Arcgis Suggest
    """
    serializer_class = serializers.GeocoderSuggestSerializer
    queryset = ''

    def list(self, request):
        q = request.query_params.get('q', None)
        c = request.query_params.get('c', None)
        if q is None:
            raise exceptions.ValidationError(
                {'detail': 'expected \'q\' parameter'}
            )
        else:
            try:
                res = PuntoBusqueda.objects.buscar_arcgis_suggest(q, c)
                ser = self.get_serializer(res, many=True)
                return Response(ser.data)
            except ObjectDoesNotExist:
                return Response([])


class ReverseGeocoderView(viewsets.GenericViewSet):

    def list(self, request):
        q = request.query_params.get('q', None)
        c = request.query_params.get('c', None)
        if q is None:
            raise exceptions.ValidationError(
                {'detail': 'expected \'q\' parameter'}
            )
        res = PuntoBusqueda.objects.reverse_geocode(q, c)
        return Response(res)


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class RecorridosPorCiudad(viewsets.ModelViewSet):
    serializer_class = serializers.RecorridoModelSerializer
    # pagination_class = pagination.PageNumberPagination
    depth = 1

    def get_queryset(self):
        show_linked = self.request.query_params.get('showall', False)

        qs = Recorrido.objects \
            .select_related('linea') \
            .filter(ciudades=self.kwargs.get('ciudad_id'))
        if show_linked:
            return qs
        return qs.filter(osm_id__isnull=True)


@api_view(['GET'])
def best_matches(request, ciudad_id):
    # return Response(recorrido_id)
    with connection.cursor() as cursor:
        query = """
            select cr.id, cr.osm_id, cr.nombre, cl.nombre as linea_nombre, ST_AsEWKT(cr.ruta) as ruta, cr.linea_id, ca.area
            from core_recorrido cr
            join crossed_areas ca on cr.id = ca.recorrido_id
            join core_linea cl on (cr.linea_id = cl.id)
            join catastro_ciudad_recorridos ccr on (ccr.recorrido_id = cr.id)
            where
            ccr.ciudad_id = %(ciudad_id)s
            and ca.area = (select min(area) from crossed_areas ca2 where ca2.recorrido_id = cr.id group by ca2.recorrido_id)
            order by ca.area
        """
        opts = {"ciudad_id": ciudad_id}
        cursor.execute(query, opts)

        response = dictfetchall(cursor)
        # adapt the response to client code
        for r in response:
            linea_id = r.pop('linea_id')
            nombre = r.pop('linea_nombre')
            r['linea'] = {'id': linea_id, 'nombre': nombre}
    return Response(response)


@api_view(['GET'])
def match_recorridos(request, recorrido_id):
    show_linked = request.query_params.get('showall', False)
    # return Response(recorrido_id)
    with connection.cursor() as cursor:
        query1 = """
            select
                ca.*, cr1.osm_id as linked_osm_id, cr2.id as linked_recorrido_id
            from
                crossed_areas ca
            left join core_recorrido cr1 on (ca.recorrido_id = cr1.id)
            left join core_recorrido cr2 on (ca.osm_id = cr2.osm_id)
            where
                recorrido_id = %(recorrido_id)s
        """
        query2 = """
            and
                ca.osm_id not in (select osm_id from core_recorrido where osm_id is not null)
        """
        query3 = """
            order by
                area asc;
        """

        if show_linked:
            query = query1 + query3
        else:
            query = query1 + query2 + query3
        opts = {"recorrido_id": recorrido_id}
        cursor.execute(query, opts)
        # return Response(recorrido_id)

        response = dictfetchall(cursor)
    return Response(response)


@api_view(['POST'])
def set_osm_pair(request):
    pass


@api_view(['GET'])
def display_recorridos(request):
    pass


class UserViewSet(viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)

    def list(self, request):
        permissions = []
        if request.user.is_staff:
            permissions.append('staff')
        return Response({
            'username': request.user.username,
            'firstName': request.user.first_name,
            'lastName': request.user.last_name,
            'email': request.user.email,
            'permissions': permissions
        })


class ImporterLogViewSet(viewsets.ModelViewSet):
    # pagination_class = pagination.PageNumberPagination
    serializer_class = serializers.ImporterLogSerializer

    def get_queryset(self):
        return ImporterLog.objects.raw("""
            SELECT
                *
            FROM
                core_importerlog
            WHERE
                run_timestamp = (
                    SELECT
                        max(run_timestamp)
                    FROM
                        core_importerlog
                )
            ORDER BY
                status desc
        """)


@api_view(['GET'])
def importerlog_stats(request):
    with connection.cursor() as cursor:
        query = """
        select
            run_timestamp,
            json_agg(json_build_object(status, count)) as series
        from (
            select
                run_timestamp,
                status,
                count(status) as count
            from
                core_importerlog
            group by
                status,
                run_timestamp
            order by
                run_timestamp,
                status
            ) as x
        where
            status is not null
        group by
            run_timestamp
        """
        cursor.execute(query)
        response = dictfetchall(cursor)
    return Response(response)
