# Generated by Django 2.2.1 on 2019-06-22 20:00

from django.db import migrations

def add_initial_ruta_simple(apps, schema_editor):
    Recorrido = apps.get_model('core', 'Recorrido')
    for r in Recorrido.objects.all():
        r.ruta_simple = r.ruta.simplify(0.0001, True)
        r.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_recorrido_ruta_simple'),
    ]

    operations = [
        migrations.RunPython(add_initial_ruta_simple, migrations.RunPython.noop),
    ]