# -*- coding: UTF-8 -*-
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.db.models import Manager as GeoManager
from django.apps import apps

from apps.catastro.models import Ciudad

from uuid import uuid4


MODERATION_CHOICES = (
    ('E', 'Esperando Mod'),
    ('S', 'Aceptado'),
    ('N', 'Rechazado'),
    ('R', 'Retirado'),
)


class RecorridoProposed(models.Model):
    uuid = models.UUIDField(default=uuid4)
    nombre = models.CharField(max_length=100)
    img_panorama = models.ImageField(max_length=200, upload_to='recorrido', blank=True, null=True)
    img_cuadrada = models.ImageField(max_length=200, upload_to='recorrido', blank=True, null=True)
    linea = models.ForeignKey('core.Linea', on_delete=models.CASCADE)
    ruta = models.LineStringField()
    sentido = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(max_length=200, blank=True, null=True)
    inicio = models.CharField(max_length=100, blank=True, null=True)
    fin = models.CharField(max_length=100, blank=True, null=True)
    semirrapido = models.BooleanField(default=False)
    color_polilinea = models.CharField(max_length=20, blank=True, null=True)
    horarios = models.TextField(blank=True, null=True)
    pois = models.TextField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    paradas_completas = models.BooleanField(default=False)

    osm_id = models.BigIntegerField(blank=True, null=True)
    osm_version = models.BigIntegerField(blank=True, null=True)

    recorrido = models.ForeignKey('core.Recorrido', on_delete=models.CASCADE)
    parent = models.UUIDField(default=uuid4)
    current_status = models.CharField(max_length=1, choices=MODERATION_CHOICES, default='E')

    date_create = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    @classmethod
    def from_recorrido(cls, recorrido):
        recorrido_model = apps.get_app_config('core').get_model("Recorrido")
        fields = [f.column for f in recorrido_model._meta.get_fields() if hasattr(f, 'column')]
        rp_dict = recorrido.__dict__.copy()
        rp_dict.pop('_state')
        rp_dict.pop('id')
        rp_dict.pop('last_updated')
        for (k, v) in list(rp_dict.items()):
            if k not in fields:
                rp_dict.pop(k)
        rp_dict['parent'] = rp_dict.pop('uuid')
        rp_dict['recorrido'] = recorrido
        return cls(**rp_dict)

    @property
    def ciudades(self):
        return Ciudad.objects.filter(lineas=self.linea)

    objects = GeoManager()

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(RecorridoProposed, self).save(*args, **kwargs)
        mod = self.get_moderacion_last()
        if mod is None or ( user is not None and user != mod.created_by ):
            self.logmoderacion_set.create(created_by=user)

    def get_current_status_display(self):
        status_list = self.logmoderacion_set.all()
        if not status_list.ordered:
            status_list = status_list.order_by('-date_create')
        if status_list:
            return status_list[0].get_newStatus_display()
        else:
            return None

    def log(self):
        return self.logmoderacion_set.order_by('-date_create')

    def get_moderacion_last(self):
        loglist = self.logmoderacion_set.order_by('-date_create')
        if loglist:
            return loglist[0]
        else:
            return None

    def get_moderacion_last_user(self):
        loglist = self.logmoderacion_set.filter(created_by__is_staff=False).order_by('-date_create')
        if loglist:
            return loglist[0].created_by
        else:
            return AnonymousUser()

    def get_pretty_user(self):
        user = self.get_moderacion_last_user()
        if user.is_anonymous:
            return "Usuario Anónimo"
        else:
            if user.first_name or user.last_name:
                return user.first_name + " " + user.last_name
            else:
                return user.username

    # def get_fb_uid(self):
    #     last = self.get_moderacion_last_user()
    #     if last != AnonymousUser():
    #         return last.social_auth.get(provider='facebook').uid
    #     else:
    #         return None

    def __unicode__(self):
        return str(self.linea) + " - " + self.nombre

    def aprobar(self, user):
        r = self.recorrido
        if not r.uuid:
            # todavia no existe una version de este recorrido real, que estoy por retirar
            # antes de retirarlo creo su version correspondiente
            rp = RecorridoProposed.from_recorrido(r)
            rp.save(user=user)
            self.parent = rp.uuid
            self.save()

        recorrido_model = apps.get_app_config('core').get_model("Recorrido")
        fields = [f.column for f in recorrido_model._meta.get_fields() if hasattr(f, 'column')]
        rp_dict = r.__dict__.copy()
        rp_dict.pop('_state')
        rp_dict.pop('id')
        rp_dict.pop('last_updated')
        for (k, v) in list(rp_dict.items()):
            if k in fields:
                setattr(r, k, getattr(self, k))
        r.save()

        try:
            parent = RecorridoProposed.objects.get(uuid=self.parent)
            if parent:
                parent.logmoderacion_set.create(created_by=user,newStatus='R')
        except RecorridoProposed.DoesNotExist:
            pass
        for rp in RecorridoProposed.objects.filter(current_status='S', recorrido=r).exclude(uuid=self.uuid):
            rp.logmoderacion_set.create(created_by=user, newStatus='R')
        self.logmoderacion_set.create(created_by=user, newStatus='S')

        #call_command('crear_thumbs', recorrido_id=self.recorrido.id)

        # Notificacion por facebook
        # token = urllib2.urlopen('https://graph.facebook.com/oauth/access_token?client_id='+settings.FACEBOOK_APP_ID+'&client_secret='+settings.FACEBOOK_API_SECRET+'&grant_type=client_credentials').read().split('access_token=')[1]
        # user = self.get_moderacion_last_user()
        # if not user.is_anonymous():
            # enviar notificacion de facebook al usuario
            #fb = user.social_auth.filter(provider='facebook')
            #if len(fb) != 0:
            #    from facebook import GraphAPI
            #    fb_uid = fb[0].uid
            #    graph = GraphAPI(token)
            #    graph.request("/"+fb_uid+"/notifications/", post_args={"template":'Felicitaciones! Un moderador aceptó tu edición en cualbondi', "href":"https://cualbondi.com.ar/revision/" + str(self.id) + "/"})

    def get_absolute_url(self):
        url = reverse('revision_externa',
            kwargs={
                'id_revision': self.id,
            })
        print("URL: " + url)
        return url

    class Meta:
        permissions = (
            ("moderate_recorridos", "Can moderate (accept/decline) recorridos"),
        )


class LogModeracion(models.Model):
    recorridoProposed = models.ForeignKey(RecorridoProposed, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    date_create = models.DateTimeField(auto_now_add=True)
    # Nuevo Estado de la moderación
    newStatus = models.CharField( max_length=1, choices=MODERATION_CHOICES, default='E')

    def save(self, *args, **kwargs):
        super(LogModeracion, self).save(*args, **kwargs)
        if self.recorridoProposed.current_status != self.newStatus:
            self.recorridoProposed.current_status = self.newStatus
            self.recorridoProposed.save()
