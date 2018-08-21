from django.contrib.gis.db import models
from django.db.models import Manager as GeoManager
from django.template.defaultfilters import slugify
from django.urls import reverse
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill

from .managers import (
    CiudadManager, ZonaManager, PuntoBusquedaManager)


class Provincia(models.Model):
    # Obligatorios
    nombre = models.CharField(max_length=100, blank=False, null=False)
    slug = models.SlugField(max_length=120, blank=True, null=False)

    # Opcionales
    variantes_nombre = models.CharField(max_length=150, blank=True, null=True)
    longitud_poligono = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    area_poligono = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    centro = models.PointField(blank=True, null=True)
    poligono = models.PolygonField(blank=True, null=True)

    objects = GeoManager()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nombre)
        if self.poligono:
            self.centro = self.poligono.centroid
        super(Provincia, self).save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Ciudad(models.Model):
    # Obligatorios
    nombre = models.CharField(max_length=100, blank=False, null=False)
    slug = models.SlugField(max_length=120, blank=True, null=False)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE)
    activa = models.BooleanField(blank=True, null=False, default=False)

    # Opcionales
    img_panorama = models.ImageField(max_length=200, upload_to='ciudad', blank=True, null=True)
    img_cuadrada = models.ImageField(max_length=200, upload_to='ciudad', blank=True, null=True)
    variantes_nombre = models.CharField(max_length=150, blank=True, null=True)
    recorridos = models.ManyToManyField('core.Recorrido', related_name='ciudades', blank=True)
    lineas = models.ManyToManyField('core.Linea', related_name='ciudades', blank=True)
    longitud_poligono = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    area_poligono = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    poligono = models.PolygonField(blank=True, null=True)
    envolvente = models.PolygonField(blank=True, null=True)
    zoom = models.IntegerField(blank=True, null=True, default=14)
    centro = models.PointField(blank=True, null=True)
    descripcion = models.TextField(null=True, blank=True)
    sugerencia = models.CharField(max_length=100, blank=True, null=True)

    objects = CiudadManager()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nombre)
        # if self.poligono:
        #    self.centro = self.poligono.centroid
        super(Ciudad, self).save(*args, **kwargs)

    def __str__(self):
        return self.nombre + " (" + self.provincia.nombre + ")"

    def get_absolute_url(self):
        return reverse('ver_ciudad', kwargs={'nombre_ciudad': self.slug})


class ImagenCiudad(models.Model):
    ciudad = models.ForeignKey(Ciudad, blank=False, null=False, on_delete=models.CASCADE)
    original = models.ImageField(
        upload_to='img/ciudades',
        blank=False,
        null=False
    )
    custom_890x300 = ImageSpecField(
        [ResizeToFill(890, 300)],
        source='original',
        format='JPEG',
        options={'quality': 100}
    )

    def _custom_890x300(self):
        try:
            return self.custom_890x300
        except:
            return None

    custom_890x300 = property(_custom_890x300)

    titulo = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.original.name + " (" + self.ciudad.nombre + ")"


class Zona(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    geo = models.GeometryField(srid=4326, geography=True)

    objects = ZonaManager()

    def __str__(self):
        return self.name


class Calle(models.Model):
    way = models.GeometryField(srid=4326, geography=True)
    nom_normal = models.TextField()
    nom = models.TextField()
    objects = GeoManager()


class Poi(models.Model):
    """ Un "Punto de interes" es algun lugar representativo
        de una "Ciudad". Por ej: la catedral de La Plata.
    """
    nom_normal = models.TextField()
    nom = models.TextField()
    slug = models.SlugField(max_length=150)
    latlng = models.GeometryField(srid=4326, geography=True)
    img_panorama = models.ImageField(max_length=200, upload_to='poi', blank=True, null=True)
    img_cuadrada = models.ImageField(max_length=200, upload_to='poi', blank=True, null=True)
    objects = GeoManager()

    def save(self, *args, **kwargs):
        slug = slugify(self.nom)
        self.slug = slug
        suffix = 2
        while Poi.objects.filter(slug=self.slug).exists():
            self.slug = "%s-%d" % (slug, suffix)
            suffix = suffix + 1
        super(Poi, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('poi', kwargs={'slug': self.slug})


class Interseccion(models.Model):
    """ Una "Interseccion" es entre 2 calles de osm
    """
    nom_normal = models.TextField()
    nom = models.TextField()
    slug = models.SlugField(max_length=150)
    latlng = models.GeometryField(srid=4326, geography=True)
    objects = GeoManager()

    def save(self, *args, **kwargs):
        slug = slugify(self.nom)
        self.slug = slug
        suffix = 2
        while Interseccion.objects.filter(slug=self.slug).exists():
            self.slug = "%s-%d" % (slug, suffix)
            suffix = suffix + 1
        super(Interseccion, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('interseccion', kwargs={'slug': self.slug})


# de http://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string/517974#517974
import unicodedata


def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nkfd_form if not unicodedata.combining(c)])


class Poicb(models.Model):
    """ Un "Punto de interes" pero que pertenece a cualbondi.
        Cualquier poi que agreguemos para nosotros, tiene
        que estar aca. Esta tabla no se regenera al importar
        pois desde osm.
    """
    nom_normal = models.TextField(blank=True)
    nom = models.TextField()
    latlng = models.GeometryField(srid=4326, geography=True)
    objects = GeoManager()

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        self.nom_normal = remove_accents(self.nom).upper()
        super(Poicb, self).save(*args, **kwargs)
        p = Poi(nom_normal=self.nom_normal, nom=self.nom, latlng=self.latlng)
        p.save()


class PuntoBusqueda(models.Model):
    nombre = models.TextField()
    precision = models.FloatField()
    geom = models.TextField()
    tipo = models.TextField()

    objects = PuntoBusquedaManager()

    def asDict(self):
        return {
            "nombre": self.nombre,
            "precision": self.precision,
            "geom": self.geom,
            "tipo": self.tipo
        }

    class Meta:
        abstract = True
