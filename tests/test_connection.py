import unittest
from urlparse import urljoin

try:
    from unittest import mock
except ImportError:
    import mock

from syncano import connect
from syncano.connection import Connection
from syncano.exceptions import SyncanoValueError, SyncanoRequestError


class ConnectTestCase(unittest.TestCase):

    @mock.patch('syncano.connection.Connection')
    def test_connect(self, connection_mock):
        connection_mock.return_value = connection_mock
        self.assertFalse(connection_mock.called)

        connection = connect(1, 2, 3, a=1, b=2, c=3)
        connection_mock.assert_called_once_with(1, 2, 3, a=1, b=2, c=3)

        self.assertTrue(connection_mock.called)
        self.assertEqual(connection, connection_mock)


class ConnectionTestCase(unittest.TestCase):

    def setUp(self):
        self.connection = Connection()

    def test_init(self):
        pass

    def test_build_params(self):
        self.connection.api_key = 'test'
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

        self.assertEqual(params['data'], '{"a": 1}')

    def test_build_url(self):
        result = urljoin(self.connection.host, 'test/')
        self.assertEqual(self.connection.build_url('test'), result)
        self.assertEqual(self.connection.build_url('/test'), result)
        self.assertEqual(self.connection.build_url('/test/'), result)
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

        content = self.connection.request('POST', 'test', result_class=mock.MagicMock)
        self.assertIsInstance(content, mock.MagicMock)

        make_request_mock.return_value = {
            'objects': [],
            'next': None,
            'prev': None,
        }
        content = self.connection.request('POST', 'test')
        self.assertIsInstance(content, self.connection.RESULT_SET_CLASS)

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
        post_mock.return_value = mock.MagicMock(status_code=401, text='Invalid email or password.')
        self.assertFalse(post_mock.called)
        self.assertIsNone(self.connection.api_key)

        with self.assertRaises(SyncanoRequestError) as cm:
            self.connection.authenticate(email='dummy', password='dummy')

        self.assertEqual(cm.exception.status_code, 401)
        self.assertEqual(cm.exception.message, 'Invalid email or password.')

        self.assertTrue(post_mock.called)
        self.assertIsNone(self.connection.api_key)

        post_mock.assert_called_once_with(
            urljoin(self.connection.host, self.connection.AUTH_SUFFIX),
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
