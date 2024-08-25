from django.core.management.base import BaseCommand
from apps.catastro.models import AdministrativeArea
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count


class Command(BaseCommand):
    help = 'remove duplicated areas'

    """
      select
        osm_type,
        osm_id,
        count(*),
        array_agg(id),
        array_agg(st_area(geometry)),
        array_agg(name)
      from
        catastro_administrativearea
      group by
        osm_type,
        osm_id
      having
        count(*)>1
      ;
    """

    def handle(self, *args, **options):
        aa = AdministrativeArea.objects.values('osm_type', 'osm_id').order_by().annotate(ids=ArrayAgg('id'), count_id=Count('id')).filter(count_id__gt=1)            

        total = len(aa)
        i = 0
        for a in aa:
            i = i + 1
            print(f'[{i*100/total:2f}] {i}/{total}: ,', end='', flush=True)
            a0 = AdministrativeArea.objects.get(id=a['ids'][0])
            a1 = AdministrativeArea.objects.get(id=a['ids'][1])
            print(f'{a0.osm_type} {a0.osm_id} {a0.name} - {a1.osm_type} {a1.osm_id} {a1.name}', end='', flush=True)
            d0 = a0.get_depth()
            d1 = a1.get_depth()
            d0parent = a0.get_parent()
            d1parent = a1.get_parent()
            d0childs = a0.get_children_count()
            d1childs = a1.get_children_count()
            if d0childs > 0 or d1childs > 0:
                print(f'Cant choose {a0.osm_type} {a0.osm_id} {a0.name} because has childs')
                continue
            if d0 > d1:
                print(f'Choosing less depth')
                a1.delete()
            elif d0 < d1:
                print(f'Choosing less depth')
                a0.delete()
            else:
                areadiff = d0parent.geometry.area - d1parent.geometry.area
                if areadiff > 0.00001:
                    print(f'Choosing bigger parent area by a margin of 0.00001')
                    a0.delete()
                elif areadiff < -0.00001:
                    print(f'Choosing bigger parent area by a margin of 0.00001')
                    a1.delete()
                else:
                    print(f'Cant choose {a0.osm_type} {a0.osm_id} {a0.name} because has same area by a margin of 0.00001')
