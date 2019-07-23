# Generated by Django 2.2.1 on 2019-07-22 09:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_auto_20190624_1823'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorrido',
            name='paradas',
            field=models.ManyToManyField(blank=True, related_name='recorridos', through='core.Horario', to='core.Parada'),
        ),
    ]
