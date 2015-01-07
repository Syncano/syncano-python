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
        pass

    def test_make_request(self):
        pass

    @mock.patch('syncano.connection.Connection.make_request')
    def test_already_authenticated(self, make_request_mock):
        self.assertIsNone(self.connection.api_key)
        self.assertFalse(make_request_mock.called)

        self.connection.api_key = 'Ala has cat'
        out = self.connection.authenticate()

        self.assertEqual(out, 'Ala has cat')
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

    def test_successful_authentication(self):
        pass
