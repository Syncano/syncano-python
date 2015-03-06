import unittest
from urlparse import urljoin

try:
    from unittest import mock
except ImportError:
    import mock

from syncano import connect, connect_instance
from syncano.connection import Connection
from syncano.exceptions import SyncanoValueError, SyncanoRequestError


class ConnectTestCase(unittest.TestCase):

    @mock.patch('syncano.models.registry')
    @mock.patch('syncano.connection.default_connection.open')
    def test_connect(self, open_mock, registry_mock):
        registry_mock.return_value = registry_mock

        self.assertFalse(registry_mock.called)
        self.assertFalse(open_mock.called)

        connection = connect(1, 2, 3, a=1, b=2, c=3)
        open_mock.assert_called_once_with(1, 2, 3, a=1, b=2, c=3)

        self.assertTrue(open_mock.called)
        self.assertEqual(connection, registry_mock)

    @mock.patch('syncano.connection.default_connection.open')
    @mock.patch('syncano.models.registry')
    @mock.patch('syncano.INSTANCE')
    def test_env_instance(self, instance_mock, registry_mock, *args):
        self.assertFalse(registry_mock.set_default_instance.called)

        connect(1, 2, 3, a=1, b=2, c=3)

        self.assertTrue(registry_mock.set_default_instance.called)
        registry_mock.set_default_instance.assert_called_once_with(instance_mock)


class ConnectInstanceTestCase(unittest.TestCase):

    @mock.patch('syncano.connect')
    def test_connect_instance(self, connect_mock):
        connect_mock.return_value = connect_mock
        get_mock = connect_mock.Instance.please.get
        get_mock.return_value = get_mock

        self.assertFalse(connect_mock.called)
        self.assertFalse(get_mock.called)

        instance = connect_instance('test-name', a=1, b=2)

        self.assertTrue(connect_mock.called)
        self.assertTrue(get_mock.called)

        connect_mock.assert_called_once_with(a=1, b=2)
        get_mock.assert_called_once_with('test-name')
        self.assertEqual(instance, get_mock)

    @mock.patch('syncano.connect')
    @mock.patch('syncano.INSTANCE')
    def test_env_connect_instance(self, instance_mock, connect_mock):
        connect_mock.return_value = connect_mock
        get_mock = connect_mock.Instance.please.get
        get_mock.return_value = get_mock

        self.assertFalse(connect_mock.called)
        self.assertFalse(get_mock.called)

        instance = connect_instance(a=1, b=2)

        self.assertTrue(connect_mock.called)
        self.assertTrue(get_mock.called)

        connect_mock.assert_called_once_with(a=1, b=2)
        get_mock.assert_called_once_with(instance_mock)
        self.assertEqual(instance, get_mock)


class ConnectionTestCase(unittest.TestCase):

    def setUp(self):
        self.connection = Connection()

    def test_init(self):
        pass

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
        self.assertEqual(params['headers']['Authorization'], 'ApiKey {0}'.format(self.connection.api_key))

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
        response_mock = mock.MagicMock(
            status_code=200,
            headers={
                'content-type': 'application/json'
            },
        )
        response_mock.json.return_value = {'ok': 'ok'}
        post_mock.return_value = response_mock

        out = self.connection.make_request('POST', 'test')
        self.assertTrue(post_mock.called)
        self.assertEqual(out, response_mock.json.return_value)

    def test_invalid_method_name(self):
        with self.assertRaises(SyncanoValueError):
            self.connection.make_request('INVALID', 'test')

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

        post_mock.assert_called_once_with(
            urljoin(self.connection.host, '{0}/'.format(self.connection.AUTH_SUFFIX)),
            headers={'content-type': self.connection.CONTENT_TYPE},
            data='{"password": "dummy", "email": "dummy"}',
            timeout=30
        )

    @mock.patch('syncano.connection.Connection.make_request')
    def test_successful_authentication(self, make_request):
        make_request.return_value = {'account_key': 'test'}
        self.assertFalse(make_request.called)
        self.assertIsNone(self.connection.api_key)

        api_key = self.connection.authenticate(email='dummy', password='dummy')

        self.assertTrue(make_request.called)
        self.assertIsNotNone(self.connection.api_key)
        self.assertEqual(self.connection.api_key, api_key)


class DefaultConnectionTestCase(unittest.TestCase):
    pass


class ConnectionMixinTestCase(unittest.TestCase):
    pass
