# Generated by Django 2.1.1 on 2018-10-14 00:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_recorrido_osm_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='recorrido',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.RunSQL("""
            UPDATE core_recorrido
            SET last_updated = (
                select
                    max(er.date_update) as date_update
                from
                    editor_recorridoproposed er
                where
                    core_recorrido.uuid = er.parent
            )
        """)
    ]
