# Generated by Django 2.2.1 on 2019-06-05 21:16

import django.contrib.postgres.fields.hstore
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_auto_20190530_1156'),
    ]

    operations = [
        migrations.AddField(
            model_name='linea',
            name='import_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parada',
            name='import_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parada',
            name='osm_id',
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='parada',
            name='tags',
            field=django.contrib.postgres.fields.hstore.HStoreField(null=True),
        ),
        migrations.AddField(
            model_name='recorrido',
            name='import_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
