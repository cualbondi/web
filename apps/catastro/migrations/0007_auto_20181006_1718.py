# Generated by Django 2.1.1 on 2018-10-06 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catastro', '0006_auto_20180928_0500'),
    ]

    operations = [
        migrations.AddField(
            model_name='calle',
            name='osm_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='interseccion',
            name='osm_id1',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='interseccion',
            name='osm_id2',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='poi',
            name='osm_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
