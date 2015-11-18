import unittest
from datetime import datetime

from syncano.exceptions import SyncanoDoesNotExist, SyncanoRequestError, SyncanoValueError
from syncano.models import CodeBox, CodeBoxTrace, Instance, Object, Webhook, WebhookTrace, User

try:
    from unittest import mock
except ImportError:
    import mock


class CloneTestCase(unittest.TestCase):
    pass


class ManagerDescriptorTestCase(unittest.TestCase):
    pass


class RelatedManagerDescriptorTestCase(unittest.TestCase):
    pass


class ManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Instance
        self.manager = Instance.please

    def tearDown(self):
        field_name = self.get_name_from_fields()
        if field_name is not None:
            field_name.default = None

        self.model = None
        self.manager = None

    def get_name_from_fields(self):
        names = [f for f in self.model._meta.fields
                 if f.name == 'name']
        if len(names) > 0:
            return names[0]
        return

    def test_create(self):
        model_mock = mock.MagicMock()
        model_mock.return_value = model_mock
        model_mock.save.return_value = model_mock
        self.manager.model = model_mock

        self.assertFalse(model_mock.called)
        instance = self.manager.create(a=1, b=2)

        self.assertTrue(model_mock.called)
        self.assertTrue(model_mock.save.called)
        self.assertEqual(instance, model_mock)

        model_mock.assert_called_once_with(a=1, b=2, is_lazy=False)
        model_mock.save.assert_called_once_with()

    @mock.patch('syncano.models.bulk.ModelBulkCreate.make_batch_request')
    def test_bulk_create(self, create_mock):
        self.assertFalse(create_mock.called)
        self.manager.bulk_create(
            User(instance_name='A', username='a', password='a'),
            User(instance_name='A', username='b', password='b')
        )
        self.assertTrue(create_mock.called)
        self.assertEqual(create_mock.call_count, 1)

    @mock.patch('syncano.models.manager.Manager.create')
    @mock.patch('syncano.models.manager.Manager.update')
    @mock.patch('syncano.models.manager.Manager.delete')
    def test_batch(self, delete_mock, update_mock, create_mock):
        self.assertFalse(delete_mock.called)
        self.assertFalse(update_mock.called)
        self.assertFalse(create_mock.called)
        self.assertFalse(self.manager.is_lazy)
        self.manager.batch(
            self.manager.as_batch().update(id=2, a=1, b=3, name='Nabuchodonozor'),
            self.manager.as_batch().create(a=2, b=3, name='Nabuchodonozor'),
            self.manager.as_batch().delete(id=3, name='Nabuchodonozor'),
        )
        self.assertFalse(self.manager.is_lazy)
        self.assertEqual(delete_mock.call_count, 1)
        self.assertEqual(update_mock.call_count, 1)
        self.assertEqual(create_mock.call_count, 1)

    @mock.patch('syncano.models.archetypes.Model.batch_object')
    def test_batch_object(self, batch_mock):
        self.assertFalse(batch_mock.called)
        self.manager.batch(
            self.manager.as_batch().create(a=2, b=3, name='Nabuchodonozor'),
        )
        self.assertTrue(batch_mock.called)
        self.assertEqual(batch_mock.call_count, 1)

    @mock.patch('syncano.models.manager.Manager.request')
    def test_batch_request(self, request_mock):
        self.assertFalse(request_mock.called)
        self.manager.batch(
            self.manager.as_batch().update(a=2, b=3, name='Nabuchodonozor'),
        )
        self.assertFalse(request_mock.called)  # shouldn't be called when batch mode is on;
        self.manager.update(a=2, b=3, name='Nabuchodonozor')
        self.assertTrue(request_mock.called)
        self.assertEqual(request_mock.call_count, 1)

    @mock.patch('syncano.models.manager.Manager.request')
    @mock.patch('syncano.models.manager.Manager._filter')
    @mock.patch('syncano.models.manager.Manager._clone')
    def test_get(self, clone_mock, filter_mock, request_mock):
        clone_mock.return_value = self.manager
        request_mock.return_value = request_mock

        self.assertFalse(filter_mock.called)
        self.assertFalse(request_mock.called)

        result = self.manager.get(1, 2, a=1, b=2)
        self.assertEqual(request_mock, result)

        self.assertTrue(filter_mock.called)
        self.assertTrue(request_mock.called)

        filter_mock.assert_called_once_with(1, 2, a=1, b=2)
        request_mock.assert_called_once_with()

        self.assertEqual(self.manager.method, 'GET')
        self.assertEqual(self.manager.endpoint, 'detail')

    @mock.patch('syncano.models.manager.Manager.get')
    def test_detail(self, get_mock):
        get_mock.return_value = get_mock

        self.assertFalse(get_mock.called)

        result = self.manager.detail(1, 2, a=1, b=2)
        self.assertEqual(get_mock, result)

        self.assertTrue(get_mock.called)
        get_mock.assert_called_once_with(1, 2, a=1, b=2)

    @mock.patch('syncano.models.manager.Manager.get')
    @mock.patch('syncano.models.manager.Manager.create')
    def test_get_or_create(self, create_mock, get_mock):
        create_mock.return_value = create_mock
        get_mock.return_value = get_mock

        # Get
        instance, created = self.manager.get_or_create(a=1, b=2, defaults={'x': 1, 'y': 2})
        self.assertEqual(instance, get_mock)
        self.assertFalse(created)

        self.assertFalse(create_mock.called)
        self.assertTrue(get_mock.called)
        get_mock.assert_called_once_with(a=1, b=2)

        create_mock.reset_mock()
        get_mock.reset_mock()

        create_mock.return_value = create_mock
        get_mock.side_effect = self.manager.model.DoesNotExist

        # Create
        instance, created = self.manager.get_or_create(a=1, b=2, defaults={'x': 1, 'y': 2})
        self.assertEqual(instance, create_mock)
        self.assertTrue(created)

        self.assertTrue(get_mock.called)
        get_mock.assert_called_once_with(a=1, b=2)

        self.assertTrue(create_mock.called)
        create_mock.assert_called_once_with(y=2, x=1, b=2, a=1)

    @mock.patch('syncano.models.manager.Manager.request')
    @mock.patch('syncano.models.manager.Manager._filter')
    @mock.patch('syncano.models.manager.Manager._clone')
    def test_delete(self, clone_mock, filter_mock, request_mock):
        clone_mock.return_value = self.manager
        request_mock.return_value = request_mock

        self.assertFalse(filter_mock.called)
        self.assertFalse(request_mock.called)

        result = self.manager.delete(1, 2, a=1, b=2)
        self.assertEqual(request_mock, result)

        self.assertTrue(filter_mock.called)
        self.assertTrue(request_mock.called)

        filter_mock.assert_called_once_with(1, 2, a=1, b=2)
        request_mock.assert_called_once_with()

        self.assertEqual(self.manager.method, 'DELETE')
        self.assertEqual(self.manager.endpoint, 'detail')

    @mock.patch('syncano.models.manager.Manager.request')
    @mock.patch('syncano.models.manager.Manager._filter')
    @mock.patch('syncano.models.manager.Manager._clone')
    def test_update(self, clone_mock, filter_mock, request_mock):
        clone_mock.return_value = self.manager
        request_mock.return_value = request_mock

        self.assertFalse(filter_mock.called)
        self.assertFalse(request_mock.called)

        result = self.manager.update(1, 2, a=1, b=2, data={'x': 1, 'y': 2})
        self.assertEqual(request_mock, result)

        self.assertTrue(filter_mock.called)
        self.assertTrue(request_mock.called)

        filter_mock.assert_called_once_with(1, 2, a=1, b=2)
        request_mock.assert_called_once_with()

        self.assertEqual(self.manager.method, 'PATCH')
        self.assertEqual(self.manager.endpoint, 'detail')
        self.assertEqual(self.manager.data, {'x': 1, 'y': 2})

        result = self.manager.update(1, 2, a=1, b=2, x=3, y=2)
        self.assertEqual(request_mock, result)

        self.assertEqual(self.manager.method, 'PATCH')
        self.assertEqual(self.manager.endpoint, 'detail')
        self.assertEqual(self.manager.data, {'x': 3, 'y': 2, 'a': 1, 'b': 2})

    @mock.patch('syncano.models.manager.Manager.update')
    @mock.patch('syncano.models.manager.Manager.create')
    def test_update_or_create(self, create_mock, update_mock):
        create_mock.return_value = create_mock
        update_mock.return_value = update_mock

        # Update
        instance, created = self.manager.update_or_create(a=1, b=2, defaults={'x': 1, 'y': 2})
        self.assertEqual(instance, update_mock)
        self.assertFalse(created)

        self.assertFalse(create_mock.called)
        self.assertTrue(update_mock.called)
        update_mock.assert_called_once_with(a=1, b=2)

        create_mock.reset_mock()
        update_mock.reset_mock()

        create_mock.return_value = create_mock
        update_mock.side_effect = self.manager.model.DoesNotExist

        # Create
        instance, created = self.manager.update_or_create(a=1, b=2, defaults={'x': 1, 'y': 2})
        self.assertEqual(instance, create_mock)
        self.assertTrue(created)

        self.assertTrue(update_mock.called)
        update_mock.assert_called_once_with(a=1, b=2)

        self.assertTrue(create_mock.called)
        create_mock.assert_called_once_with(y=2, x=1, b=2, a=1)

    @mock.patch('syncano.models.manager.Manager.list')
    @mock.patch('syncano.models.manager.Manager._clone')
    def test_all(self, clone_mock, list_mock):
        clone_mock.return_value = self.manager
        list_mock.return_value = list_mock

        self.assertFalse(clone_mock.called)
        self.assertFalse(list_mock.called)

        self.manager._limit = 10
        result = self.manager.all(1, 2, a=1, b=2)
        self.assertEqual(result, list_mock)
        self.assertIsNone(self.manager._limit)

        self.assertTrue(clone_mock.called)
        self.assertTrue(list_mock.called)
        list_mock.assert_called_once_with(1, 2, a=1, b=2)

    @mock.patch('syncano.models.manager.Manager._filter')
    @mock.patch('syncano.models.manager.Manager._clone')
    def test_list(self, clone_mock, filter_mock):
        clone_mock.return_value = self.manager

        self.assertFalse(clone_mock.called)
        self.assertFalse(filter_mock.called)

        self.manager.list(1, 2, a=1, b=2)

        self.assertTrue(clone_mock.called)
        self.assertTrue(filter_mock.called)
        filter_mock.assert_called_once_with(1, 2, a=1, b=2)

        self.assertEqual(self.manager.method, 'GET')
        self.assertEqual(self.manager.endpoint, 'list')

    @mock.patch('syncano.models.options.Options.get_endpoint_properties')
    @mock.patch('syncano.models.manager.Manager._clone')
    def test_set_default_properties(self, get_endpoint_mock, clone_mock):
        get_endpoint_mock.return_value = ['a', 'b', 'name']
        clone_mock.return_value = self.manager

        instance_name = self.get_name_from_fields()
        instance_name.default = 'test_original'

        self.manager._set_default_properties(get_endpoint_mock())
        self.assertDictEqual(self.manager.properties,
                             {'name': 'test_original'})

    @mock.patch('syncano.models.manager.Manager.list')
    def test_first(self, list_mock):
        list_mock.__getitem__.return_value = 1
        list_mock.return_value = list_mock

        self.assertFalse(list_mock.called)

        result = self.manager.first(1, 2, a=1, b=2)
        self.assertEqual(result, 1)
        self.assertTrue(list_mock.called)
        list_mock.assert_called_once_with(1, 2, a=1, b=2)

        list_mock.reset_mock()
        list_mock.side_effect = KeyError

        result = self.manager.first(1, 2, a=1, b=2)
        self.assertIsNone(result)
        self.assertTrue(list_mock.called)
        list_mock.assert_called_once_with(1, 2, a=1, b=2)

    @mock.patch('syncano.models.manager.Manager._clone')
    def test_page_size(self, clone_mock):
        clone_mock.return_value = self.manager

        self.manager.page_size(10)
        self.assertEqual(self.manager.query['page_size'], 10)

        with self.assertRaises(SyncanoValueError):
            self.manager.page_size('invalid value')

    @mock.patch('syncano.models.manager.Manager._clone')
    def test_limit(self, clone_mock):
        clone_mock.return_value = self.manager

        self.manager.limit(10)
        self.assertEqual(self.manager._limit, 10)

        with self.assertRaises(SyncanoValueError):
            self.manager.limit('invalid value')

    @mock.patch('syncano.models.manager.Manager._clone')
    def test_raw(self, clone_mock):
        clone_mock.return_value = self.manager

        self.assertTrue(self.manager._serialize)
        self.manager.raw()
        self.assertFalse(self.manager._serialize)

    def test_serialize(self):
        model = mock.Mock()
        self.manager.model = mock.Mock

        result = self.manager.serialize(model)
        self.assertEqual(result, model)

        with self.assertRaises(SyncanoValueError):
            self.manager.serialize(True)

        result = self.manager.serialize({'a': 1, 'b': 2})
        self.assertIsInstance(result, mock.Mock)

        self.manager._serialize = False
        result = self.manager.serialize({'a': 1, 'b': 2})
        self.assertEqual(result, {'a': 1, 'b': 2})

    @mock.patch('syncano.models.manager.Manager.connection')
    def test_request(self, connection_mock):
        self.manager.query = {'a': 1}
        self.manager.data = {'b': 2}

        request_mock = connection_mock.request
        request_mock.return_value = {}

        self.assertFalse(request_mock.called)
        self.manager.request()
        self.assertTrue(request_mock.called)

        request_mock.assert_called_once_with(
            'GET',
            u'/v1/instances/',
            data={'b': 2},
            params={'a': 1}
        )

        request_mock.return_value = {'next': 'url'}
        result = self.manager.request()
        self.assertEqual(result, {'next': 'url'})

        request_mock.side_effect = SyncanoRequestError(status_code=404, reason='404')
        with self.assertRaises(SyncanoDoesNotExist):
            self.manager.request()

        request_mock.side_effect = SyncanoRequestError(status_code=500, reason='404')
        with self.assertRaises(SyncanoRequestError):
            self.manager.request()

        request_mock.side_effect = SyncanoValueError
        with self.assertRaises(SyncanoValueError):
            self.manager.request()

        self.manager.method = 'dummy'
        with self.assertRaises(SyncanoValueError):
            self.manager.request()

    @mock.patch('syncano.models.manager.Manager.request')
    def test_iterator(self, request_mock):
        request_mock.side_effect = [
            {
                'next': 'next_url',
                'objects': [{'a': 1}, {'b': 2}]
            },
            {
                'next': None,
                'objects': [{'c': 3}, {'d': 4}]
            }
        ]

        self.manager._limit = 3
        self.manager.model = mock.Mock

        results = list(self.manager.iterator())
        self.assertEqual(len(results), 3)

        self.assertTrue(request_mock.called)
        self.assertEqual(request_mock.call_count, 2)
        request_mock.assert_called_with(path='next_url')

    def test_get_allowed_method(self):
        self.manager.endpoint = 'detail'

        result = self.manager.get_allowed_method('GET', 'POST')

        self.assertEqual(result, 'GET')

        result = self.manager.get_allowed_method('DELETE', 'POST')
        self.assertEqual(result, 'DELETE')

        with self.assertRaises(SyncanoValueError):
            self.manager.get_allowed_method('dummy')


class CodeBoxManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.model = CodeBox
        self.manager = CodeBox.please

    @mock.patch('syncano.models.manager.CodeBoxManager.request')
    @mock.patch('syncano.models.manager.CodeBoxManager._filter')
    @mock.patch('syncano.models.manager.CodeBoxManager._clone')
    def test_run(self, clone_mock, filter_mock, request_mock):
        clone_mock.return_value = self.manager
        request_mock.return_value = {'id': 10}

        self.assertFalse(filter_mock.called)
        self.assertFalse(request_mock.called)

        result = self.manager.run(1, 2, a=1, b=2, payload={'x': 1, 'y': 2})
        self.assertIsInstance(result, CodeBoxTrace)

        self.assertTrue(filter_mock.called)
        self.assertTrue(request_mock.called)

        filter_mock.assert_called_once_with(1, 2, a=1, b=2)
        request_mock.assert_called_once_with()

        self.assertEqual(self.manager.method, 'POST')
        self.assertEqual(self.manager.endpoint, 'run')
        self.assertEqual(self.manager.data['payload'], '{"y": 2, "x": 1}')


class WebhookManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Webhook
        self.manager = Webhook.please

    @mock.patch('syncano.models.manager.WebhookManager.request')
    @mock.patch('syncano.models.manager.WebhookManager._filter')
    @mock.patch('syncano.models.manager.WebhookManager._clone')
    def test_run(self, clone_mock, filter_mock, request_mock):
        clone_mock.return_value = self.manager
        request_mock.return_value = {
            'status': 'success',
            'duration': 937,
            'result': '1',
            'executed_at': '2015-03-16T11:52:14.172830Z'
        }

        self.assertFalse(filter_mock.called)
        self.assertFalse(request_mock.called)

        result = self.manager.run(1, 2, a=1, b=2, payload={'x': 1, 'y': 2})
        self.assertIsInstance(result, WebhookTrace)
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.duration, 937)
        self.assertEqual(result.result, '1')
        self.assertIsInstance(result.executed_at, datetime)

        self.assertTrue(filter_mock.called)
        self.assertTrue(request_mock.called)

        filter_mock.assert_called_once_with(1, 2, a=1, b=2)
        request_mock.assert_called_once_with()

        self.assertEqual(self.manager.method, 'POST')
        self.assertEqual(self.manager.endpoint, 'run')
        self.assertEqual(self.manager.data['payload'], '{"y": 2, "x": 1}')


class ObjectManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Object
        self.manager = Object.please

    @mock.patch('syncano.models.Object.get_subclass_model')
    def test_create(self, get_subclass_model_mock):
        model_mock = mock.MagicMock()
        model_mock.return_value = model_mock
        get_subclass_model_mock.return_value = model_mock

        self.assertFalse(model_mock.called)
        self.assertFalse(get_subclass_model_mock.called)
        instance = self.manager.create(a=1, b=2)
        self.assertTrue(model_mock.called)
        self.assertTrue(model_mock.save.called)
        self.assertTrue(get_subclass_model_mock.called)
        self.assertEqual(instance, model_mock)

        model_mock.assert_called_once_with(a=1, b=2, is_lazy=False)
        model_mock.save.assert_called_once_with()
        get_subclass_model_mock.assert_called_once_with(a=1, b=2, is_lazy=False)

    @mock.patch('syncano.models.Object.get_subclass_model')
    def test_serialize(self, get_subclass_model_mock):
        get_subclass_model_mock.return_value = mock.Mock
        self.manager.properties['instance_name'] = 'test'
        self.manager.properties['class_name'] = 'test'

        self.assertFalse(get_subclass_model_mock.called)
        self.manager.serialize({})
        self.assertTrue(get_subclass_model_mock.called)
        get_subclass_model_mock.assert_called_once_with(instance_name='test', class_name='test')

    @mock.patch('syncano.models.manager.ObjectManager._clone')
    @mock.patch('syncano.models.Object.get_subclass_model')
    def test_filter(self, get_subclass_model_mock, clone_mock):
        get_subclass_model_mock.return_value = Instance
        clone_mock.return_value = self.manager

        self.manager.filter(name='test')
        self.assertEqual(self.manager.query['query'], '{"name": {"_eq": "test"}}')

        self.assertEqual(self.manager.method, 'GET')
        self.assertEqual(self.manager.endpoint, 'list')

        self.manager.filter(name__gt='test')
        self.assertEqual(self.manager.query['query'], '{"name": {"_gt": "test"}}')

        self.manager.filter(name__gt='test', description='test')
        self.assertEqual(self.manager.query['query'], '{"description": {"_eq": "test"}, "name": {"_gt": "test"}}')

        with self.assertRaises(SyncanoValueError):
            self.manager.filter(dummy_field=4)

        with self.assertRaises(SyncanoValueError):
            self.manager.filter(name__xx=4)

    @mock.patch('syncano.models.manager.Manager._clone')
    def test_order_by(self, clone_mock):
        clone_mock.return_value = self.manager

        self.manager.order_by('field')
        self.assertEqual(self.manager.query['order_by'], 'field')

        with self.assertRaises(SyncanoValueError):
            self.manager.order_by(10)


# TODO
class SchemaManagerTestCase(unittest.TestCase):
    pass
