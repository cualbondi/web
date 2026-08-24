from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('core', '0026_importerlog_type'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'CREATE INDEX CONCURRENTLY IF NOT EXISTS core_recorrido_osm_id_idx '
                        'ON core_recorrido (osm_id);'
                    ),
                    reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS core_recorrido_osm_id_idx;',
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='recorrido',
                    index=models.Index(fields=['osm_id'], name='core_recorrido_osm_id_idx'),
                ),
            ],
        ),
    ]
