# Generated by Django 2.2.1 on 2019-06-22 19:49

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_auto_20190618_2053'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorrido',
            name='ruta_simple',
            field=django.contrib.gis.db.models.fields.LineStringField(null=True, srid=4326),
        ),
    ]
