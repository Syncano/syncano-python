import unittest

from syncano.exceptions import SyncanoValidationError, SyncanoValueError
from syncano.models import Field, Instance
from syncano.models.options import Options


class Meta:
    _private_method = 1
    non_existing_method = 1
    plural_name = 'test'
    related_name = 'tests'
    parent = 'Instance'

    endpoints = {
        'detail': {
            'methods': ['delete', 'post', 'patch', 'get'],
            'path': '/v1.1/dummy/{name}/',
        },
        'list': {
            'methods': ['post', 'get'],
            'path': '/v1.1/dummy/',
        },
        'dummy': {
            'methods': ['post', 'get'],
            'path': '/v1.1/dummy/{a}/{b}/',
            'properties': ['a', 'b']
        }
    }


class OptionsTestCase(unittest.TestCase):

    def setUp(self):
        self.options = Options(Meta)

    def test_meta_inheritance(self):
        self.assertFalse(hasattr(self.options, '_private_method'))
        self.assertFalse(hasattr(self.options, 'non_existing_method'))
        self.assertEqual(self.options.plural_name, 'test')
        self.assertEqual(self.options.related_name, 'tests')

    def test_build_properties(self):
        endpoints = self.options.endpoints
        self.assertTrue('properties' in endpoints['detail'])
        self.assertTrue('name' in endpoints['detail']['properties'])

        self.assertTrue('properties' in endpoints['list'])
        self.assertEqual(endpoints['list']['properties'], [])

        self.assertTrue('properties' in endpoints['dummy'])
        self.assertEqual(endpoints['dummy']['properties'], ['a', 'b'])

    def test_contribute_to_class(self):

        class Model:
            pass

        self.options.plural_name = None
        self.options.related_name = None
        self.options.contribute_to_class(Model, 'please')

        self.assertTrue(hasattr(Model, 'please'))
        self.assertEqual(self.options.name, 'Model')
        self.assertEqual(self.options.plural_name, 'Models')
        self.assertEqual(self.options.related_name, 'models')
        self.assertEqual(self.options.parent, Instance)

    def test_resolve_parent_data(self):
        self.options.parent = Instance
        self.options.resolve_parent_data()
        self.assertTrue(self.options.parent_resolved)

    def test_add_field(self):
        field = Field(name='test')
        self.options.add_field(field)
        self.assertTrue(field.name in self.options.field_names)
        self.assertTrue(field in self.options.fields)

        with self.assertRaises(SyncanoValueError):
            self.options.add_field(field)

    def test_get_field(self):
        field = Field(name='test')
        self.options.add_field(field)

        with self.assertRaises(SyncanoValueError):
            self.options.get_field('')

        with self.assertRaises(SyncanoValueError):
            self.options.get_field(1)

        with self.assertRaises(SyncanoValueError):
            self.options.get_field('invalid_field_name')

        self.assertEqual(self.options.get_field('test'), field)

    def test_get_endpoint(self):
        with self.assertRaises(SyncanoValueError):
            self.options.get_endpoint('invalid_endpoint')

        self.assertEqual(
            self.options.get_endpoint('list'),
            self.options.endpoints['list']
        )

    def test_get_endpoint_properties(self):
        with self.assertRaises(SyncanoValueError):
            self.options.get_endpoint_properties('invalid_endpoint')

        self.assertEqual(
            self.options.get_endpoint_properties('list'),
            self.options.endpoints['list']['properties']
        )

    def test_get_endpoint_path(self):
        with self.assertRaises(SyncanoValueError):
            self.options.get_endpoint_path('invalid_endpoint')

        self.assertEqual(
            self.options.get_endpoint_path('list'),
            self.options.endpoints['list']['path']
        )

    def test_get_endpoint_methods(self):
        with self.assertRaises(SyncanoValueError):
            self.options.get_endpoint_methods('invalid_endpoint')

        self.assertEqual(
            self.options.get_endpoint_methods('list'),
            self.options.endpoints['list']['methods']
        )

    def test_resolve_endpoint(self):
        with self.assertRaises(SyncanoValueError):
            self.options.resolve_endpoint('dummy', {})

        properties = {'instance_name': 'test', 'a': 'a', 'b': 'b'}
        path = self.options.resolve_endpoint('dummy', properties)

        self.assertEqual(path, '/v1.1/instances/test/v1.1/dummy/a/b/')

    def test_get_endpoint_query_params(self):
        properties = {'instance_name': 'test', 'x': 'y'}
        params = self.options.get_endpoint_query_params('dummy', properties)
        self.assertEqual(params, {'x': 'y'})

    def test_get_path_properties(self):
        path = '/{a}/{b}-{c}/dummy-{d}/'
        properties = self.options.get_path_properties(path)
        self.assertEqual(properties, ['a', 'b'])

    def test_resolve_endpoint_with_missing_http_method(self):
        properties = {'instance_name': 'test'}
        with self.assertRaises(SyncanoValidationError):
            self.options.resolve_endpoint('list', properties, 'DELETE')

    def test_resolve_endpoint_with_specified_http_method(self):
        properties = {'instance_name': 'test', 'a': 'a', 'b': 'b'}
        path = self.options.resolve_endpoint('dummy', properties, 'GET')
        self.assertEqual(path, '/v1.1/instances/test/v1.1/dummy/a/b/')
