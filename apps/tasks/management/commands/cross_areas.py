from django.core.management.base import BaseCommand
from apps.commands.cross_areas import CrossAreasTask


class Command(BaseCommand):
    help = "calculate intersection areas between osm and cb to find matches"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        CrossAreasTask().run()
