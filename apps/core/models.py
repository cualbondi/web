import uuid
from datetime import datetime

from django.contrib.gis.db import models
from django.contrib.postgres.fields import HStoreField
from django.db.models import Manager as GeoManager
from django.template.defaultfilters import slugify
from django.core.serializers import serialize

from apps.catastro.models import Ciudad
from ..utils.reverse import reverse
from .managers import RecorridoManager


class Linea(models.Model):
    import_timestamp = models.DateTimeField(blank=True, null=True)
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, blank=True, null=False)
    descripcion = models.TextField(blank=True, null=True)
    foto = models.CharField(max_length=20, blank=True, null=True)
    img_panorama = models.ImageField(max_length=200, upload_to='linea', blank=True, null=True)
    img_cuadrada = models.ImageField(max_length=200, upload_to='linea', blank=True, null=True)
    color_polilinea = models.CharField(max_length=20, blank=True, null=True)
    info_empresa = models.TextField(blank=True, null=True)
    info_terminal = models.TextField(blank=True, null=True)
    localidad = models.CharField(max_length=50, blank=True, null=True)
    cp = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=200, blank=True, null=True)
    envolvente = models.PolygonField(blank=True, null=True)
    osm_id = models.BigIntegerField(blank=True, null=True)

    @property
    def geoJSON(self):
        return serialize(
            'geojson',
            [self],
            geometry_field='envolvente',
            fields=('nombre',)
        )

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nombre)
        super(Linea, self).save(*args, **kwargs)

    def get_absolute_url(self, argentina=None):
        sid = self.osm_id
        tid = 'r'
        if self.osm_id is None:
            sid = self.id
            tid = 'c'
        return reverse(
            'ver_linea',
            kwargs={
                'osm_type': tid,
                'osm_id': sid,
                'slug': self.slug,
            },
            argentina=argentina
        )


class Recorrido(models.Model):
    import_timestamp = models.DateTimeField(blank=True, null=True)
    uuid = models.UUIDField(default=uuid.uuid4)
    nombre = models.CharField(max_length=200)
    img_panorama = models.ImageField(max_length=200, upload_to='recorrido', blank=True, null=True)
    img_cuadrada = models.ImageField(max_length=200, upload_to='recorrido', blank=True, null=True)
    linea = models.ForeignKey(Linea, related_name='recorridos', on_delete=models.CASCADE, null=True)
    ruta = models.LineStringField()
    ruta_simple = models.LineStringField(null=True)
    sentido = models.CharField(max_length=200, blank=True, null=True)
    slug = models.SlugField(max_length=200, blank=True, null=False)
    inicio = models.CharField(max_length=200, blank=True, null=True)
    fin = models.CharField(max_length=200, blank=True, null=True)
    semirrapido = models.BooleanField(default=False)
    color_polilinea = models.CharField(max_length=20, blank=True, null=True)
    horarios = models.TextField(blank=True, null=True)
    pois = models.TextField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    osm_id = models.BigIntegerField(blank=True, null=True)
    osm_version = models.BigIntegerField(blank=True, null=True)
    ruta_last_updated = models.DateTimeField(default=datetime.now)
    # Si tiene las paradas completas es porque tiene todas las paradas de
    # este recorrido en la tabla paradas+horarios (horarios puede ser null),
    # y se puede utilizar en la busqueda usando solo las paradas.
    paradas_completas = models.BooleanField(default=False)
    type = models.CharField(max_length=30, blank=True, null=True)
    king = models.BigIntegerField(blank=True, null=True, default=286393)  # default = argentina osm_id

    @property
    def geoJSON(self):
        return serialize(
            'geojson',
            [self],
            geometry_field='ruta',
            fields=('nombre',)
        )

    objects = RecorridoManager()

    paradas = models.ManyToManyField('core.Parada', related_name='recorridos', through='core.Horario', blank=True)

    @property
    def ciudades(self):
        return Ciudad.objects.filter(lineas=self.linea)

    def __str__(self):
        # return str(self.ciudades.all()[0]) + " - " + str(self.linea) + " - " + self.nombre
        return str(self.linea) + " - " + self.nombre

    def save(self, *args, **kwargs):
        # Generar el SLUG a partir del origen y destino del recorrido
        try:
            self.slug = slugify(self.nombre + " desde " + self.inicio + " hasta " + self.fin)
        except Exception:
            self.slug = slugify(self.nombre)

        self.ruta_simple = self.ruta.simplify(0.0001, True)

        # # Asegurarse de que no haya 'inicio' y/o 'fin' invalidos
        # assert (
        #     self.inicio != self.fin
        #     and self.inicio != ''
        #     and self.fin != ''
        # ), "Los campos 'inicio' y 'fin' no pueden ser vacios y/o iguales"

        # Ejecutar el SAVE original
        super(Recorrido, self).save(*args, **kwargs)

    class Meta:
        ordering = ['linea__nombre', 'nombre']

    def get_absolute_url(self, argentina=None):
        sid = self.osm_id
        tid = 'w'
        if self.osm_id is None:
            sid = self.id
            tid = 'c'
        return reverse(
            'ver_recorrido',
            kwargs={
                'osm_type': tid,
                'osm_id': sid,
                'slug': self.slug,
            },
            argentina=argentina
        )


class Posicion(models.Model):
    """Ubicacion geografica de un recorrido en cierto momento del tiempo"""

    class Meta:
        verbose_name = 'Posicion'
        verbose_name_plural = 'Posiciones'

    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    dispositivo_uuid = models.CharField(max_length=200, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    latlng = models.PointField()

    objects = GeoManager()

    def __str__(self):
        return '{recorrido} ({hora}) - {punto}'.format(
            recorrido=self.recorrido,
            punto=self.latlng,
            hora=self.timestamp.strftime("%d %h %Y %H:%M:%S")
        )


class Comercio(models.Model):
    nombre = models.CharField(max_length=200)
    latlng = models.PointField()
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE)
    objects = GeoManager()


class Parada(models.Model):
    import_timestamp = models.DateTimeField(blank=True, null=True)
    osm_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    tags = HStoreField(null=True)
    codigo = models.CharField(max_length=15, blank=True, null=True)
    nombre = models.CharField(max_length=200, blank=True, null=True)
    latlng = models.PointField()

    objects = GeoManager()

    def __str__(self):
        return self.nombre or self.codigo or "{}, {}".format(self.latlng.x, self.latlng.y)

    def get_absolute_url(self, argentina=None):
        return reverse(
            'ver_parada',
            kwargs={
                'id': self.id
            },
            argentina=argentina
        )


class Horario(models.Model):
    """ Un "Recorrido" pasa por una "Parada" a
        cierto "Horario". "Horario" es el modelo
        interpuesto entre "Recorrido" y "Parada"
    """
    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    hora = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return str(self.recorrido) + " - " + str(self.parada) + " - " + str(self.hora or ' ')


class Terminal(models.Model):
    linea = models.ForeignKey(Linea, on_delete=models.CASCADE)
    descripcion = models.TextField(blank=True, null=True)
    direccion = models.CharField(max_length=150)
    telefono = models.CharField(max_length=150)
    latlng = models.PointField()
    objects = GeoManager()


class Tarifa(models.Model):
    tipo = models.CharField(max_length=150)
    precio = models.DecimalField(max_digits=5, decimal_places=2)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE)

    def __str__(self):
        return '{0} - {1} - ${2}'.format(self.ciudad, self.tipo, self.precio)


class FacebookPage(models.Model):
    id_fb = models.CharField(max_length=50)
    linea = models.ForeignKey(Linea, on_delete=models.CASCADE)


class ImporterLog(models.Model):
    osm_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    osm_version = models.BigIntegerField(blank=True, null=True)
    osm_timestamp = models.DateTimeField(blank=True, null=True)
    run_timestamp = models.DateTimeField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.TextField(blank=True, null=True, db_index=True)
    proposed = models.BooleanField()
    accepted = models.BooleanField()
    proposed_reason = models.TextField(blank=True, null=True)
    accepted_reason = models.TextField(blank=True, null=True)
    king = models.TextField(blank=True, null=True)

    # additional info to show log context and be able to search on something
    osm_administrative = models.TextField(blank=True, null=True)
    osm_name = models.TextField(blank=True, null=True)

    def __str__(self):
        return "[{}] {} {}".format(
            self.run_timestamp,
            self.osm_id,
            self.osm_timestamp
        )
