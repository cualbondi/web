# Generated by Django 2.1.1 on 2018-10-06 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_merge_20180928_0455'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorrido',
            name='osm_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]