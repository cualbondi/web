# Generated by Django 2.2.1 on 2019-06-24 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_auto_20190622_2000'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorrido',
            name='king',
            field=models.BigIntegerField(blank=True, default=286393, null=True),
        ),
        migrations.AddField(
            model_name='recorrido',
            name='type',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
