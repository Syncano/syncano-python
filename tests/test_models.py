import unittest
from datetime import datetime

from syncano.exceptions import SyncanoValidationError, SyncanoValueError
from syncano.models import (CodeBox, CodeBoxTrace, Instance, Object, Webhook,
                            WebhookTrace)

try:
    from unittest import mock
except ImportError:
    import mock


class ModelTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Instance()

    def test_init(self):
        self.assertTrue(hasattr(self.model, '_raw_data'))
        self.assertEquals(self.model._raw_data, {})

        model = Instance(name='test', dummy_field='dummy')
        self.assertTrue('name' in model._raw_data)
        self.assertTrue('dummy_field' not in model._raw_data)

    def test_repr(self):
        expected = '<{0}: {1}>'.format(
            self.model.__class__.__name__,
            self.model.pk
        )
        out = repr(self.model)
        self.assertEqual(out, expected)

    def test_str(self):
        expected = '<{0}: {1}>'.format(
            self.model.__class__.__name__,
            self.model.pk
        )
        out = str(self.model)
        self.assertEqual(out, expected)

    def test_unicode(self):
        expected = u'<{0}: {1}>'.format(
            self.model.__class__.__name__,
            self.model.pk
        )
        out = unicode(self.model)
        self.assertEqual(out, expected)

    def test_eq(self):
        model_one = Instance(name='one')
        model_two = Instance(name='two')
        self.assertNotEqual(model_one, model_two)
        self.assertNotEqual(model_one, 1)
        self.assertNotEqual(True, model_two)

    def test_get_connection(self):
        connection = self.model._get_connection()
        self.assertEqual(connection, self.model._meta.connection)
        connection = self.model._get_connection(connection=1)
        self.assertEqual(connection, 1)

    @mock.patch('syncano.models.Instance._get_connection')
    def test_create(self, connection_mock):
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {}

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)

        Instance(name='test').save()

        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        connection_mock.request.assert_called_with(
            'POST',
            '/v1/instances/',
            data={'name': 'test'}
        )

    @mock.patch('syncano.models.Instance._get_connection')
    def test_update(self, connection_mock):
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {}

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)

        Instance(name='test', links={'self': 'dummy'}).save()

        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        connection_mock.request.assert_called_with(
            'PUT',
            '/v1/instances/test/',
            data={'name': 'test'}
        )

        Instance._meta.endpoints['detail']['methods'] = ['put']
        Instance(name='test', links={'self': 'dummy'}).save()

        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        connection_mock.request.assert_called_with(
            'PUT',
            '/v1/instances/test/',
            data={'name': 'test'}
        )

    @mock.patch('syncano.models.Instance._get_connection')
    def test_delete(self, connection_mock):
        model = Instance(name='test', links={'self': '/v1/instances/test/'})
        connection_mock.return_value = connection_mock

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        model.delete()
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)

        connection_mock.assert_called_once_with()
        connection_mock.request.assert_called_once_with('DELETE', '/v1/instances/test/')

        model = Instance()
        with self.assertRaises(SyncanoValidationError):
            model.delete()

    @mock.patch('syncano.models.Instance._get_connection')
    def test_reload(self, connection_mock):
        model = Instance(name='test', links={'self': '/v1/instances/test/'})
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {
            'name': 'new_one',
            'description': 'dummy desc'
        }

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        self.assertIsNone(model.description)
        model.reload()
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        self.assertEqual(model.name, 'new_one')
        self.assertEqual(model.description, 'dummy desc')

        connection_mock.assert_called_once_with()
        connection_mock.request.assert_called_once_with('GET', '/v1/instances/test/')

        model = Instance()
        with self.assertRaises(SyncanoValidationError):
            model.delete()

    def test_validation(self):
        # More validation tests is present in test_fields.py
        Instance(name='test').validate()

        with self.assertRaises(SyncanoValidationError):
            Instance().validate()

    @mock.patch('syncano.models.Instance.validate')
    def test_is_valid(self, validate_mock):
        validate_mock.side_effect = [None, SyncanoValidationError]
        self.assertFalse(validate_mock.called)

        self.assertTrue(self.model.is_valid())
        self.assertFalse(self.model.is_valid())

        self.assertTrue(validate_mock.called)
        self.assertEqual(validate_mock.call_count, 2)

    def test_to_python(self):
        self.model.to_python({'name': 'test', 'dummy': 'dummy'})
        self.assertTrue(hasattr(self.model, 'name'))
        self.assertEqual(self.model.name, 'test')
        self.assertFalse(hasattr(self.model, 'dummy'))

    def test_to_native(self):
        self.model.name = 'test'
        self.model.description = 'desc'
        self.model.dummy = 'test'
        self.assertEqual(self.model.to_native(), {'name': 'test', 'description': 'desc'})


class CodeBoxTestCase(unittest.TestCase):

    def setUp(self):
        self.model = CodeBox()

    @mock.patch('syncano.models.CodeBox._get_connection')
    def test_run(self, connection_mock):
        model = CodeBox(instance_name='test', id=10, links={'run': '/v1/instances/test/codeboxes/10/run/'})
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {'id': 10}

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        result = model.run(a=1, b=2)
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        self.assertIsInstance(result, CodeBoxTrace)

        connection_mock.assert_called_once_with(a=1, b=2)
        connection_mock.request.assert_called_once_with(
            'POST', '/v1/instances/test/codeboxes/10/run/', data={'payload': '{"a": 1, "b": 2}'}
        )

        model = CodeBox()
        with self.assertRaises(SyncanoValidationError):
            model.run()


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


class WebhookTestCase(unittest.TestCase):
    def setUp(self):
        self.model = Webhook()

    @mock.patch('syncano.models.Webhook._get_connection')
    def test_run(self, connection_mock):
        model = Webhook(instance_name='test', name='name', links={'run': '/v1/instances/test/webhooks/name/run/'})
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {
            'status': 'success',
            'duration': 937,
            'result': '1',
            'executed_at': '2015-03-16T11:52:14.172830Z'
        }

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        result = model.run(x=1, y=2)
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        self.assertIsInstance(result, WebhookTrace)
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.duration, 937)
        self.assertEqual(result.result, '1')
        self.assertIsInstance(result.executed_at, datetime)

        connection_mock.assert_called_once_with(x=1, y=2)
        connection_mock.request.assert_called_once_with(
            'POST',
            '/v1/instances/test/webhooks/name/run/',
            data={'payload': '{"y": 2, "x": 1}'}
        )

        model = Webhook()
        with self.assertRaises(SyncanoValidationError):
            model.run()
