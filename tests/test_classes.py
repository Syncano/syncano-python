import unittest

from syncano.exceptions import SyncanoValueError
from syncano.models import Instance, Object

try:
    from unittest import mock
except ImportError:
    import mock


class ObjectTestCase(unittest.TestCase):

    def setUp(self):
        self.schema = [
            {
                'name': 'title',
                'type': 'string',
                'order_index': True,
                'filter_index': True
            },
            {
                'name': 'release_year',
                'type': 'integer',
                'order_index': True,
                'filter_index': True
            },
            {
                'name': 'price',
                'type': 'float',
                'order_index': True,
                'filter_index': True
            },
            {
                'name': 'author',
                'type': 'reference',
                'order_index': True,
                'filter_index': True,
                'target': 'Author'
            }
        ]

    @mock.patch('syncano.models.Object.get_subclass_model')
    def test_new(self, get_subclass_model_mock):
        get_subclass_model_mock.return_value = Instance
        self.assertFalse(get_subclass_model_mock.called)

        with self.assertRaises(SyncanoValueError):
            Object()

        with self.assertRaises(SyncanoValueError):
            Object(instance_name='dummy')

        self.assertFalse(get_subclass_model_mock.called)
        o = Object(instance_name='dummy', class_name='dummy', x=1, y=2)
        self.assertIsInstance(o, Instance)
        self.assertTrue(get_subclass_model_mock.called)
        get_subclass_model_mock.assert_called_once_with('dummy', 'dummy')

    def test_create_subclass(self):
        SubClass = Object.create_subclass('Test', self.schema)
        fields = [f for f in SubClass._meta.fields if f not in Object._meta.fields]

        self.assertEqual(SubClass.__name__, 'Test')

        for schema, field in zip(self.schema, fields):
            query_allowed = ('order_index' in schema or 'filter_index' in schema)
            self.assertEqual(schema['name'], field.name)
            self.assertEqual(field.query_allowed, query_allowed)
            self.assertFalse(field.required)
            self.assertFalse(field.read_only)

    @mock.patch('syncano.models.classes.registry')
    @mock.patch('syncano.models.Object.create_subclass')
    def test_get_or_create_subclass(self, create_subclass_mock, registry_mock):
        create_subclass_mock.return_value = 1
        registry_mock.get_model_by_name.side_effect = [2, LookupError]

        self.assertFalse(registry_mock.get_model_by_name.called)
        self.assertFalse(registry_mock.add.called)
        self.assertFalse(create_subclass_mock.called)

        model = Object.get_or_create_subclass('test', [{}, {}])
        self.assertEqual(model, 2)

        self.assertTrue(registry_mock.get_model_by_name.called)
        self.assertFalse(registry_mock.add.called)
        self.assertFalse(create_subclass_mock.called)
        registry_mock.get_model_by_name.assert_called_with('test')

        model = Object.get_or_create_subclass('test', [{}, {}])
        self.assertEqual(model, 1)

        self.assertTrue(registry_mock.get_model_by_name.called)
        self.assertTrue(registry_mock.add.called)
        self.assertTrue(create_subclass_mock.called)

        registry_mock.get_model_by_name.assert_called_with('test')
        create_subclass_mock.assert_called_with('test', [{}, {}])
        registry_mock.add.assert_called_with('test', 1)

        self.assertEqual(registry_mock.get_model_by_name.call_count, 2)
        self.assertEqual(registry_mock.add.call_count, 1)
        self.assertEqual(create_subclass_mock.call_count, 1)

    def test_get_subclass_name(self):
        self.assertEqual(Object.get_subclass_name('', ''), 'Object')
        self.assertEqual(Object.get_subclass_name('duMMY', ''), 'DummyObject')
        self.assertEqual(Object.get_subclass_name('', 'ClS'), 'ClsObject')
        self.assertEqual(Object.get_subclass_name('duMMy', 'CLS'), 'DummyClsObject')

    @mock.patch('syncano.models.Manager.get')
    def test_get_class_schema(self, get_mock):
        get_mock.return_value = get_mock
        self.assertFalse(get_mock.called)
        result = Object.get_class_schema('dummy-instance', 'dummy-class')
        self.assertTrue(get_mock.called)
        self.assertEqual(result, get_mock.schema)
        get_mock.assert_called_once_with('dummy-instance', 'dummy-class')

    @mock.patch('syncano.models.Object.create_subclass')
    @mock.patch('syncano.models.Object.get_class_schema')
    @mock.patch('syncano.models.manager.registry.get_model_by_name')
    @mock.patch('syncano.models.Object.get_subclass_name')
    @mock.patch('syncano.models.Object.fetch_schema')
    def test_get_subclass_model(self, get_subclass_name_mock, get_model_by_name_mock,
                                get_class_schema_mock, create_subclass_mock):

        create_subclass_mock.return_value = create_subclass_mock
        get_subclass_name_mock.side_effect = [
            'Object',
            'DummyObject',
            'DummyObject',
        ]

        get_model_by_name_mock.side_effect = [
            Object,
            LookupError
        ]

        result = Object.get_subclass_model('', '')
        self.assertEqual(Object, result)

        result = Object.get_subclass_model('', '')
        self.assertEqual(Object, result)

        result = Object.get_subclass_model('', '')
        self.assertEqual(create_subclass_mock, result)
