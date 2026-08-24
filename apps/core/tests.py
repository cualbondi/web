from unittest.mock import PropertyMock, patch

from django.test import RequestFactory, SimpleTestCase

from apps.core.views import ver_linea, ver_recorrido


class PublicRedirectTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @patch('apps.core.views.get_object_or_404')
    def test_line_redirects_before_accessing_geometry(self, get_object_or_404):
        linea = get_object_or_404.return_value
        linea.get_absolute_url.return_value = 'https://testserver/ar/l/r123/correct/'
        type(linea).envolvente = PropertyMock(side_effect=AssertionError('geometry accessed before redirect'))
        request = self.factory.get('/ar/l/r123/wrong/')

        response = ver_linea(request, osm_type='r', osm_id='123', slug='wrong', country_code='ar')

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'https://testserver/ar/l/r123/correct/')

    @patch('apps.core.views.get_object_or_404')
    def test_route_redirects_before_accessing_geometry(self, get_object_or_404):
        recorrido = get_object_or_404.return_value
        recorrido.get_absolute_url.return_value = 'https://testserver/ar/r/c123/correct/'
        type(recorrido).ruta = PropertyMock(side_effect=AssertionError('geometry accessed before redirect'))
        request = self.factory.get('/ar/r/c123/wrong/')

        response = ver_recorrido(request, osm_type='c', osm_id='123', slug='wrong', country_code='ar')

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'https://testserver/ar/r/c123/correct/')
