# Generated by Django 3.2.16 on 2024-08-19 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_auto_20200229_0154'),
    ]

    operations = [
        migrations.AddField(
            model_name='importerlog',
            name='type',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
