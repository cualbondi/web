from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('catastro', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ciudad',
            name='lineas',
            field=models.ManyToManyField(to='core.Linea', blank=True),
        ),
        migrations.AddField(
            model_name='ciudad',
            name='provincia',
            field=models.ForeignKey(to='catastro.Provincia', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='ciudad',
            name='recorridos',
            field=models.ManyToManyField(to='core.Recorrido', blank=True),
        ),
    ]
