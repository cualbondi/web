# Generated by Django 2.1.1 on 2018-10-21 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('editor', '0004_auto_20181020_1912'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorridoproposed',
            name='img_cuadrada',
            field=models.ImageField(blank=True, max_length=200, null=True, upload_to='recorrido'),
        ),
        migrations.AddField(
            model_name='recorridoproposed',
            name='img_panorama',
            field=models.ImageField(blank=True, max_length=200, null=True, upload_to='recorrido'),
        ),
    ]
