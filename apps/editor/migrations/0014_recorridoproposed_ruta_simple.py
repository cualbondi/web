# Generated by Django 3.2.16 on 2024-08-19 12:01

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('editor', '0013_recorridoproposed_country_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorridoproposed',
            name='ruta_simple',
            field=django.contrib.gis.db.models.fields.LineStringField(null=True, srid=4326),
        ),
    ]