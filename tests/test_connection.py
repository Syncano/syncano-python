import json
import tempfile
import unittest

import six
from syncano import connect
from syncano.connection import Connection, ConnectionMixin
from syncano.exceptions import SyncanoRequestError, SyncanoValueError
from syncano.models.registry import registry

if six.PY3:
    from urllib.parse import urljoin
else:
    from urlparse import urljoin

try:
    from unittest import mock
except ImportError:
    import mock


class ConnectTestCase(unittest.TestCase):

    @mock.patch('syncano.connection.DefaultConnection.open')
    def test_connect(self, open_mock):
        self.assertFalse(open_mock.called)

        connection = connect(1, 2, 3, a=1, b=2, c=3)
        open_mock.assert_called_once_with(1, 2, 3, a=1, b=2, c=3)

        self.assertTrue(open_mock.called)
        self.assertEqual(connection, registry)

    @mock.patch('syncano.models.registry.connection.open')
    @mock.patch('syncano.models.registry')
    @mock.patch('syncano.INSTANCE')
    def test_env_instance(self, instance_mock, registry_mock, *args):
        self.assertFalse(registry_mock.set_default_instance.called)

        connect(1, 2, 3, a=1, b=2, c=3)

        self.assertTrue(registry_mock.set_default_instance.called)
        registry_mock.set_default_instance.assert_called_once_with(instance_mock)


class ConnectionTestCase(unittest.TestCase):

    def _get_response_mock(self, **kwargs):
        return_value = kwargs.pop('return_value', None) or {'ok': 'ok'}
        defaults = {
            'status_code': 200,
            'headers': {
                'content-type': 'application/json'
            },
        }
        defaults.update(kwargs)
        response_mock = mock.MagicMock(**defaults)
        response_mock.json.return_value = return_value
        return response_mock

    def setUp(self):
        self.connection = Connection()

    @mock.patch('requests.Session.post')
    @mock.patch('syncano.connection.json.dumps')
    @mock.patch('syncano.DEBUG')
    def test_debug(self, debug_mock, dumps_mock, post_mock):
        debug_mock.return_value = True
        post_mock.return_value = self._get_response_mock()

        self.assertFalse(dumps_mock.called)
        self.connection.make_request('POST', 'test')
        self.assertTrue(dumps_mock.called)
        dumps_mock.assert_called_once_with(
            {'files': [], 'headers': {'content-type': 'application/json'}, 'timeout': 30, 'verify': False},
            sort_keys=True, indent=2, separators=(',', ': '))

    @mock.patch('requests.Session.post')
    def test_invalid_json_response(self, post_mock):
        response_mock = self._get_response_mock(text='test')
        response_mock.json.side_effect = ValueError
        post_mock.return_value = response_mock

        content = self.connection.make_request('POST', 'test')
        self.assertEqual(content, 'test')

    @mock.patch('requests.Session.post')
    def test_server_error(self, post_mock):
        response_mock = self._get_response_mock(status_code=500)
        post_mock.return_value = response_mock

        with self.assertRaises(SyncanoRequestError):
            self.connection.make_request('POST', 'test')

    @mock.patch('requests.Session.post')
    def test_client_error(self, post_mock):
        response_mock = self._get_response_mock(status_code=401)
        post_mock.return_value = response_mock

        with self.assertRaises(SyncanoRequestError):
            self.connection.make_request('POST', 'test')

    @mock.patch('syncano.logger.debug')
    @mock.patch('requests.Session.post')
    def test_other_error(self, post_mock, debug_mock):
        response_mock = self._get_response_mock(status_code=301)
        post_mock.return_value = response_mock

        self.assertFalse(debug_mock.called)
        with self.assertRaises(SyncanoRequestError):
            self.connection.make_request('POST', 'test')
        self.assertTrue(debug_mock.called)

    def test_build_params(self):
        self.connection.api_key = 'test'
        self.connection.verify_ssl = False
        empty = {'data': {'a': 1}}
        params = self.connection.build_params(empty)
        self.assertNotEqual(params, empty)

        self.assertTrue('timeout' in params)
        self.assertEqual(params['timeout'], self.connection.timeout)

        self.assertTrue('headers' in params)

        self.assertTrue('Authorization' in params['headers'])
        self.assertEqual(params['headers']['Authorization'], 'token {0}'.format(self.connection.api_key))

        self.assertTrue('content-type' in params['headers'])
        self.assertEqual(params['headers']['content-type'], self.connection.CONTENT_TYPE)

        self.assertTrue('verify' in params)
        self.assertFalse(params['verify'])

        self.assertEqual(params['data'], {'a': 1})

    def test_build_url(self):
        result = urljoin(self.connection.host, 'test/')
        result += '?q=1'
        self.assertEqual(self.connection.build_url('test?q=1'), result)
        self.assertEqual(self.connection.build_url('/test?q=1'), result)
        self.assertEqual(self.connection.build_url('/test/?q=1'), result)
        self.assertEqual(self.connection.build_url(result), result)

        with self.assertRaises(SyncanoValueError):
            self.connection.build_url(True)

    @mock.patch('syncano.connection.Connection.authenticate')
    @mock.patch('syncano.connection.Connection.make_request')
    def test_request_authentication(self, make_request_mock, authenticate_mock):
        self.assertFalse(make_request_mock.called)
        self.assertFalse(authenticate_mock.called)
        self.connection.request('POST', 'test')
        self.assertTrue(make_request_mock.called)
        self.assertTrue(authenticate_mock.called)

    @mock.patch('syncano.connection.Connection.authenticate')
    @mock.patch('syncano.connection.Connection.make_request')
    def test_request_serialization(self, make_request_mock, authenticate_mock):
        self.assertFalse(make_request_mock.called)
        self.assertFalse(authenticate_mock.called)

        make_request_mock.return_value = {'a': 1}
        content = self.connection.request('POST', 'test')

        self.assertTrue(make_request_mock.called)
        self.assertTrue(authenticate_mock.called)
        self.assertEqual(content, make_request_mock.return_value)

    @mock.patch('requests.Session.post')
    def test_make_request(self, post_mock):
        response_mock = self._get_response_mock()
        post_mock.return_value = response_mock

        out = self.connection.make_request('POST', 'test')
        self.assertTrue(post_mock.called)
        self.assertEqual(out, response_mock.json.return_value)

    def test_invalid_method_name(self):
        with self.assertRaises(SyncanoValueError):
            self.connection.make_request('INVALID', 'test')

    @mock.patch('syncano.connection.Connection.get_response_content')
    @mock.patch('requests.Session.patch')
    def test_make_request_for_creating_object_with_file(self, patch_mock, get_response_mock):
        kwargs = {
            'data': {
                'files': {'filename': tempfile.TemporaryFile(mode='w')}
            }
        }
        # if FAIL will raise TypeError for json dump
        self.connection.make_request('POST', 'test', **kwargs)

    @mock.patch('syncano.connection.Connection.get_response_content')
    @mock.patch('requests.Session.patch')
    def test_make_request_for_updating_object_with_file(self, patch_mock, get_reponse_mock):
        kwargs = {
            'data': {'filename': tempfile.TemporaryFile(mode='w')}
        }
        # if FAIL will raise TypeError for json dump
        self.connection.make_request('PATCH', 'test', **kwargs)

    @mock.patch('requests.Session.post')
    def test_request_error(self, post_mock):
        post_mock.return_value = mock.MagicMock(status_code=404, text='Invalid request')
        self.assertFalse(post_mock.called)

        with self.assertRaises(SyncanoRequestError):
            self.connection.make_request('POST', 'test')

        self.assertTrue(post_mock.called)

    def test_is_authenticated(self):
        self.assertFalse(self.connection.is_authenticated())
        self.connection.api_key = 'xxxx'
        self.assertTrue(self.connection.is_authenticated())

    @mock.patch('syncano.connection.Connection.make_request')
    def test_already_authenticated(self, make_request_mock):
        self.assertIsNone(self.connection.api_key)
        self.assertFalse(make_request_mock.called)

        self.connection.api_key = 'Ala has a cat'
        out = self.connection.authenticate()

        self.assertEqual(out, 'Ala has a cat')
        self.assertFalse(make_request_mock.called)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_authentication_empty_email(self, make_request_mock):
        self.assertFalse(make_request_mock.called)
        with self.assertRaises(SyncanoValueError):
            self.connection.authenticate()
        self.assertFalse(make_request_mock.called)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_authentication_empty_password(self, make_request_mock):
        self.assertFalse(make_request_mock.called)
        with self.assertRaises(SyncanoValueError):
            self.connection.authenticate(email='dummy')
        self.assertFalse(make_request_mock.called)

    @mock.patch('requests.Session.post')
    def test_invalid_credentials(self, post_mock):
        response = mock.MagicMock(status_code=401)
        response.json.return_value = 'Invalid email or password.'
        post_mock.return_value = response

        self.assertFalse(post_mock.called)
        self.assertIsNone(self.connection.api_key)

        with self.assertRaises(SyncanoRequestError) as cm:
            self.connection.authenticate(email='dummy', password='dummy')

        self.assertEqual(cm.exception.status_code, 401)
        self.assertEqual(cm.exception.reason, 'Invalid email or password.')

        self.assertTrue(post_mock.called)
        self.assertIsNone(self.connection.api_key)
        call_args = post_mock.call_args[0]
        call_kwargs = post_mock.call_args[1]
        call_kwargs['data'] = json.loads(call_kwargs['data'])

        self.assertEqual(call_args[0], urljoin(self.connection.host, '{0}/'.format(self.connection.AUTH_SUFFIX)))
        self.assertEqual(call_kwargs['headers'], {'content-type': self.connection.CONTENT_TYPE})
        self.assertEqual(call_kwargs['timeout'], 30)
        self.assertTrue(call_kwargs['verify'])
        self.assertDictEqual(call_kwargs['data'], {"password": "dummy", "email": "dummy"})

    @mock.patch('syncano.connection.Connection.make_request')
    def test_successful_authentication(self, make_request):
        make_request.return_value = {'account_key': 'test'}
        self.assertFalse(make_request.called)
        self.assertIsNone(self.connection.api_key)

        api_key = self.connection.authenticate(email='dummy', password='dummy')

        self.assertTrue(make_request.called)
        self.assertIsNotNone(self.connection.api_key)
        self.assertEqual(self.connection.api_key, api_key)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_get_account_info(self, make_request):
        info = {'first_name': '', 'last_name': '', 'is_active': True,
                'id': 1, 'has_password': True, 'email': 'dummy'}
        self.test_successful_authentication()
        make_request.return_value = info
        self.assertFalse(make_request.called)
        self.assertIsNotNone(self.connection.api_key)
        ret = self.connection.get_account_info()
        self.assertTrue(make_request.called)
        self.assertEqual(info, ret)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_get_account_info_with_api_key(self, make_request):
        info = {'first_name': '', 'last_name': '', 'is_active': True,
                'id': 1, 'has_password': True, 'email': 'dummy'}
        make_request.return_value = info
        self.assertFalse(make_request.called)
        self.assertIsNone(self.connection.api_key)
        ret = self.connection.get_account_info(api_key='test')
        self.assertIsNotNone(self.connection.api_key)
        self.assertTrue(make_request.called)
        self.assertEqual(info, ret)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_get_account_info_invalid_key(self, make_request):
        err = SyncanoRequestError(403, 'No such API Key.')
        make_request.side_effect = err
        self.assertFalse(make_request.called)
        self.assertIsNone(self.connection.api_key)
        try:
            self.connection.get_account_info(api_key='invalid')
            self.assertTrue(False)
        except SyncanoRequestError as e:
            self.assertIsNotNone(self.connection.api_key)
            self.assertTrue(make_request.called)
            self.assertEqual(e, err)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_get_account_info_missing_key(self, make_request):
        self.assertFalse(make_request.called)
        self.assertIsNone(self.connection.api_key)
        try:
            self.connection.get_account_info()
            self.assertTrue(False)
        except SyncanoValueError:
            self.assertIsNone(self.connection.api_key)
            self.assertFalse(make_request.called)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_get_user_info(self, make_request_mock):
        info = {'profile': {}}
        make_request_mock.return_value = info
        self.assertFalse(make_request_mock.called)
        self.connection.api_key = 'Ala has a cat'
        self.connection.user_key = 'Tom has a cat also'
        self.connection.instance_name = 'tom_ala'
        ret = self.connection.get_user_info()
        self.assertTrue(make_request_mock.called)
        self.assertEqual(info, ret)

    @mock.patch('syncano.connection.Connection.make_request')
    def test_get_user_info_without_instance(self, make_request_mock):
        info = {'profile': {}}
        make_request_mock.return_value = info
        self.assertFalse(make_request_mock.called)
        self.connection.api_key = 'Ala has a cat'
        self.connection.user_key = 'Tom has a cat also'
        self.connection.instance_name = None
        with self.assertRaises(SyncanoValueError):
            self.connection.get_user_info()

    @mock.patch('syncano.connection.Connection.make_request')
    def test_get_user_info_without_auth_keys(self, make_request_mock):
        info = {'profile': {}}
        make_request_mock.return_value = info
        self.assertFalse(make_request_mock.called)

        self.connection.api_key = None
        with self.assertRaises(SyncanoValueError):
            self.connection.get_user_info()

        self.connection.api_key = 'Ala has a cat'
        self.connection.user_key = None
        with self.assertRaises(SyncanoValueError):
            self.connection.get_user_info()


class DefaultConnectionTestCase(unittest.TestCase):

    def setUp(self):
        self.connection = registry.connection
        self.connection._connection = None

    def test_call(self):
        with self.assertRaises(SyncanoValueError):
            self.connection()

        self.connection._connection = '1234'
        self.assertEqual(self.connection(), '1234')

    @mock.patch('syncano.connection.Connection')
    def test_open(self, connection_mock):
        connection_mock.return_value = connection_mock
        self.assertFalse(connection_mock.called)
        connection = self.connection.open(a=1, b=2)
        self.assertTrue(connection_mock.called)
        self.assertEqual(connection, connection_mock)
        self.assertEqual(self.connection._connection, connection_mock)
        connection_mock.assert_called_once_with(a=1, b=2)


class ConnectionMixinTestCase(unittest.TestCase):

    def setUp(self):
        self.mixin = ConnectionMixin()

    @mock.patch('syncano.models.registry._default_connection')
    def test_getter(self, default_connection_mock):
        default_connection_mock.return_value = default_connection_mock

        self.assertFalse(default_connection_mock.called)
        connection = self.mixin.connection

        self.assertTrue(default_connection_mock.called)
        self.assertEqual(connection, default_connection_mock)

    def test_setter(self):
        connection = Connection()
        self.mixin.connection = connection
        self.assertEqual(self.mixin._connection, connection)

    def test_setter_validation(self):
        self.assertEqual(self.mixin._connection, None)
        with self.assertRaises(SyncanoValueError):
            self.mixin.connection = 4
        self.assertEqual(self.mixin._connection, None)

    def test_deleter(self):
        self.assertEqual(self.mixin._connection, None)
        connection = Connection()
        self.mixin.connection = connection
        self.assertEqual(self.mixin._connection, connection)
        del self.mixin.connection
        self.assertEqual(self.mixin._connection, None)
