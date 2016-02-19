import unittest

from syncano.exceptions import SyncanoValidationError
from syncano.models import Instance, registry

try:
    from unittest import mock
except ImportError:
    import mock


class ModelTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Instance()
        registry.connection.open()

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

    @mock.patch('syncano.models.Instance._get_connection')
    def test_save_with_revision(self, connection_mock):
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {}

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)

        Instance(name='test').save(expected_revision=12)

        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        connection_mock.request.assert_called_with(
            'POST',
            '/v1/instances/',
            data={'name': 'test', 'expected_revision': 12}
        )
