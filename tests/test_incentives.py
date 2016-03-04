# -*- coding: utf-8 -*-

import unittest
from datetime import datetime

from syncano.exceptions import SyncanoValidationError
from syncano.models import Script, ScriptTrace, ResponseTemplate, ScriptEndpoint, ScriptEndpointTrace

try:
    from unittest import mock
except ImportError:
    import mock


class ScriptTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Script()

    @mock.patch('syncano.models.Script._get_connection')
    def test_run(self, connection_mock):
        model = Script(instance_name='test', id=10, links={'run': '/v1.1/instances/test/snippets/scripts/10/run/'})
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {'id': 10}

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        result = model.run(a=1, b=2)
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        self.assertIsInstance(result, ScriptTrace)

        connection_mock.assert_called_once_with(a=1, b=2)
        connection_mock.request.assert_called_once_with(
            'POST', '/v1.1/instances/test/snippets/scripts/10/run/', data={'payload': '{"a": 1, "b": 2}'}
        )

        model = Script()
        with self.assertRaises(SyncanoValidationError):
            model.run()


class ScriptEndpointTestCase(unittest.TestCase):
    def setUp(self):
        self.model = ScriptEndpoint()

    @mock.patch('syncano.models.ScriptEndpoint._get_connection')
    def test_run(self, connection_mock):
        model = ScriptEndpoint(instance_name='test', name='name',
                               links={'run': '/v1.1/instances/test/endpoints/scripts/name/run/'})
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = {
            'status': 'success',
            'duration': 937,
            'result': {u'stdout': 1, u'stderr': u''},
            'executed_at': '2015-03-16T11:52:14.172830Z'
        }

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        result = model.run(x=1, y=2)
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        self.assertIsInstance(result, ScriptEndpointTrace)
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.duration, 937)
        self.assertEqual(result.result, {u'stdout': 1, u'stderr': u''})
        self.assertIsInstance(result.executed_at, datetime)

        connection_mock.assert_called_once_with(x=1, y=2)
        connection_mock.request.assert_called_once_with(
            'POST',
            '/v1.1/instances/test/endpoints/scripts/name/run/',
            data={"y": 2, "x": 1}
        )

        model = ScriptEndpoint()
        with self.assertRaises(SyncanoValidationError):
            model.run()


class ResponseTemplateTestCase(unittest.TestCase):
    def setUp(self):
        self.model = ResponseTemplate

    @mock.patch('syncano.models.ResponseTemplate._get_connection')
    def test_render(self, connection_mock):
        model = self.model(instance_name='test', name='name',
                           links={'run': '/v1.1/instances/test/snippets/templates/name/render/'})
        connection_mock.return_value = connection_mock
        connection_mock.request.return_value = '<div>12345</div>'

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        response = model.render()
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        self.assertEqual(response, '<div>12345</div>')

        connection_mock.request.assert_called_once_with(
            'POST',
            '/v1.1/instances/test/snippets/templates/name/render/',
            data={'context': {}}
        )
