# Generated by Django 2.0.6 on 2018-08-20 23:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catastro', '0004_auto_20180802_0105'),
    ]

    operations = [
        migrations.AddField(
            model_name='poi',
            name='img_cuadrada',
            field=models.ImageField(blank=True, max_length=200, null=True, upload_to='poi'),
        ),
        migrations.AddField(
            model_name='poi',
            name='img_panorama',
            field=models.ImageField(blank=True, max_length=200, null=True, upload_to='poi'),
        ),
    ]