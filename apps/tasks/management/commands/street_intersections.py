from django.core.management.base import BaseCommand
from apps.commands.street_intersections import StreetIntersectionsTask


class Command(BaseCommand):
    help = "Generate street intersections"

    def handle(self, *args, **options):
        StreetIntersectionsTask().run()
