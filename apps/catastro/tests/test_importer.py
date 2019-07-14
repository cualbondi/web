from django.core.management import call_command

from django.test import TestCase


class CommandsTestCase(TestCase):
    def test_import_osm(self):
        pass
        # args = []
        # opts = {
        #     'king': 'argentina',
        #     'download': True,
        #     'admin_areas': True,
        #     'update_routes': True,
        #     'add_routes': True,
        #     'pois': True
        # }
        # call_command('update_osm', *args, **opts)
