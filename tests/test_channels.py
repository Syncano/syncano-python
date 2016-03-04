import unittest

from syncano.models.channels import Channel, PollThread, Timeout

try:
    from unittest import mock
except ImportError:
    import mock


class PollThreadTestCase(unittest.TestCase):

    def setUp(self):
        self.connection_mock = mock.Mock()
        self.connection_mock.return_value = self.connection_mock
        self.callback_mock = mock.Mock()
        self.callback_mock.return_value = False
        self.error_mock = mock.Mock()
        self.error_mock.return_value = False
        self.endpoint = 'dummy'
        self.thread = PollThread(self.connection_mock, self.endpoint,
                                 self.callback_mock, self.error_mock)

    def test_request(self):
        self.assertFalse(self.connection_mock.request.called)
        self.thread.request()
        self.assertTrue(self.connection_mock.request.called)
        self.connection_mock.request.assert_called_once_with(
            'GET',
            self.endpoint,
            params={
                'room': self.thread.room,
                'last_id': self.thread.last_id
            },
            timeout=self.thread.timeout
        )

    def test_stop(self):
        self.assertFalse(self.thread.abort)
        self.thread.stop()
        self.assertTrue(self.thread.abort)
        self.assertIsNone(self.thread.callback)
        self.assertIsNone(self.thread.error)

    @mock.patch('syncano.models.channels.PollThread.request')
    def test_run(self, request_mock):
        request_mock.return_value = {'id': 1}
        self.assertFalse(request_mock.called)
        self.assertFalse(self.callback_mock.called)
        self.thread.run()
        self.assertTrue(request_mock.called)
        self.assertTrue(self.callback_mock.called)

    @mock.patch('syncano.models.channels.PollThread.request')
    def test_run_timeout(self, request_mock):
        request_mock.side_effect = Timeout
        self.assertFalse(request_mock.called)
        self.assertFalse(self.callback_mock.called)
        self.assertFalse(self.error_mock.called)
        self.thread.run()
        self.assertTrue(request_mock.called)
        self.assertTrue(self.callback_mock.called)
        self.assertFalse(self.error_mock.called)

    @mock.patch('syncano.models.channels.PollThread.request')
    def test_run_error(self, request_mock):
        request_mock.side_effect = Exception('dummy')
        self.assertFalse(request_mock.called)
        self.assertFalse(self.callback_mock.called)
        self.assertFalse(self.error_mock.called)
        self.thread.run()
        self.assertTrue(request_mock.called)
        self.assertFalse(self.callback_mock.called)
        self.assertTrue(self.error_mock.called)


class ChannelTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Channel()

    @mock.patch('syncano.models.channels.Channel._get_connection')
    @mock.patch('syncano.models.channels.PollThread')
    def test_poll(self, poll_thread_mock, connection_mock):
        poll_thread_mock.return_value = poll_thread_mock
        connection_mock.return_value = connection_mock

        self.assertFalse(poll_thread_mock.called)
        self.assertFalse(connection_mock.called)
        self.model.poll(room='a', last_id='b', callback='c', error='d', timeout='e')
        self.assertTrue(poll_thread_mock.called)
        self.assertTrue(connection_mock.called)
        poll_thread_mock.assert_called_once_with(
            connection_mock,
            '/v1.1/instances/None/channels/None/poll/',
            'c',
            'd',
            last_id='b',
            room='a',
            timeout='e',
            name='poll_None'
        )
        self.assertTrue(poll_thread_mock.start.called)

    @mock.patch('syncano.models.channels.Channel._get_connection')
    def test_publish(self, connection_mock):
        connection_mock.return_value = connection_mock

        self.assertFalse(connection_mock.called)
        self.assertFalse(connection_mock.request.called)
        self.model.publish({'a': 1}, 1)
        self.assertTrue(connection_mock.called)
        self.assertTrue(connection_mock.request.called)
        connection_mock.request.assert_called_once_with(
            'POST',
            '/v1.1/instances/None/channels/None/publish/',
            data={'room': u'1', 'payload': '{"a": 1}'}
        )
