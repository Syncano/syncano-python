import unittest
from datetime import datetime

from syncano.exceptions import SyncanoValidationError
from syncano.models import CodeBox, CodeBoxTrace, Webhook, WebhookTrace

try:
    from unittest import mock
except ImportError:
    import mock


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
