# Generated by Django 2.1.1 on 2018-10-26 22:50

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('editor', '0005_auto_20181021_0002'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorridoproposed',
            name='ruta_last_updated',
            field=models.DateTimeField(default=datetime.datetime.now, null=True),
        ),
        migrations.RunSQL("""
            UPDATE editor_recorridoproposed
            SET ruta_last_updated = date_update
        """)
    ]
