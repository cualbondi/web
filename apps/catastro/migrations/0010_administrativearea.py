# Generated by Django 2.1.4 on 2019-01-17 02:42

import django.contrib.gis.db.models.fields
import django.contrib.postgres.fields.hstore
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catastro', '0009_poi_tags'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdministrativeArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lft', models.PositiveIntegerField(db_index=True)),
                ('rgt', models.PositiveIntegerField(db_index=True)),
                ('tree_id', models.PositiveIntegerField(db_index=True)),
                ('depth', models.PositiveIntegerField(db_index=True)),
                ('osm_type', models.CharField(choices=[('r', 'Relation'), ('w', 'Way'), ('n', 'Node')], db_index=True, max_length=1)),
                ('osm_id', models.BigIntegerField(db_index=True)),
                ('name', models.TextField()),
                ('geometry', django.contrib.gis.db.models.fields.GeometryField(srid=4326)),
                ('tags', django.contrib.postgres.fields.hstore.HStoreField()),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
